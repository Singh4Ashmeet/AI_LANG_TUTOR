from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from ..config import settings
from ..database import admin_logs_collection, grammar_stats_collection, vocabulary_collection

PERSONA_PROMPTS = {
    "friendly": (
        "You are a warm, encouraging language learning friend. Use casual tone, "
        "celebrate small wins with genuine enthusiasm. When correcting, always lead "
        "with what they got right first."
    ),
    "strict": (
        "You are a disciplined language coach. Correct every grammatical error "
        "immediately after responding to their meaning. Be precise and direct. "
        "No excessive praise."
    ),
    "funny": (
        "You are a witty tutor who loves wordplay. Make jokes when appropriate, "
        "keep the atmosphere light. Never sacrifice accuracy for humor."
    ),
    "professor": (
        "You are a patient linguistics professor. When you correct an error, explain "
        "the underlying grammatical rule in the student's native language."
    ),
}

CEFR_RULES = {
    "A1": "Use only present tense. Max 5 words per sentence. Very common vocabulary only.",
    "A2": "Use present + simple past. Short sentences. Avoid complex clauses.",
    "B1": "Use present, past, future. Introduce common idioms. Medium sentence length.",
    "B2": "Use all main tenses including subjunctive. Natural sentence variety. Idioms.",
    "C1": "Full natural register. Complex syntax. Nuanced vocabulary. Near-native.",
    "C2": "Native speaker level. All registers. Cultural references. No simplification.",
}


async def build_system_prompt(user: dict) -> str:
    grammar = await grammar_stats_collection().find(
        {"user_id": user["_id"], "mastery": {"$lt": 0.5}}
    ).sort("mastery", 1).to_list(length=3)
    vocab = await vocabulary_collection().find(
        {"user_id": user["_id"], "status": "learning"}
    ).to_list(length=5)

    grammar_rules = [item.get("rule") for item in grammar]
    vocab_words = [item.get("word") for item in vocab]

    persona = PERSONA_PROMPTS.get(user.get("tutor_persona") or "friendly")
    cefr = user.get("cefr_level", "A1")

    return "\n".join(
        [
            f"Native language: {user.get('native_language')}",
            f"Target language: {user.get('target_language')}",
            f"CEFR level: {cefr}. {CEFR_RULES.get(cefr, '')}",
            f"Persona: {persona}",
            f"Goals: {', '.join(user.get('goals', []))}",
            f"Grammar weaknesses: {', '.join(grammar_rules)}",
            f"Inject learning words: {', '.join(vocab_words)}",
            "Rules: respond only in target language, bold new words, end with a question, "
            "correct errors gently, provide explanations in native language when correcting.",
        ]
    )


async def log_llm_error(message: str, metadata: dict) -> None:
    await admin_logs_collection().insert_one(
        {
            "event_type": "llm_error",
            "message": message,
            "metadata": metadata,
            "admin_id": None,
            "user_id": metadata.get("user_id"),
            "created_at": datetime.now(timezone.utc),
        }
    )


async def call_groq(messages: list[dict], system_prompt: str, stream: bool = False) -> str:
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key not configured")

    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 500,
        "temperature": 0.7,
        "stream": stream,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def call_gemini(messages: list[dict], system_prompt: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key not configured")

    text = json.dumps({"system": system_prompt, "messages": messages})
    payload = {"contents": [{"parts": [{"text": text}]}]}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def generate_reply(user: dict, messages: list[dict]) -> str:
    system_prompt = await build_system_prompt(user)
    try:
        return await call_groq(messages, system_prompt, stream=False)
    except Exception as exc:
        await log_llm_error("Groq failed", {"user_id": user["_id"], "error": str(exc)})
        return await call_gemini(messages, system_prompt)
