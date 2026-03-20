from __future__ import annotations
import json
from datetime import datetime, timezone
import httpx
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings
from ..models.admin import AdminLog
from ..models.vocabulary import VocabularyItem
from ..models.extra import GrammarStat
from ..database import get_session

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
    user_id = user.get("id") or user.get("_id")
    # Quick fix for ID
    try:
        if isinstance(user_id, str) and not user_id.isdigit(): user_id = None
        else: user_id = int(user_id)
    except: user_id = None

    grammar_rules = []
    vocab_words = []
    
    if user_id:
        async for session in get_session():
            try:
                # Grammar
                g_stmt = select(GrammarStat).where(GrammarStat.user_id == user_id).order_by(GrammarStat.errors.desc()).limit(3)
                g_res = await session.execute(g_stmt)
                grammar_rules = [item.rule for item in g_res.scalars().all()]
                
                # Vocab
                v_stmt = select(VocabularyItem).where(VocabularyItem.user_id == user_id, VocabularyItem.status == "learning").limit(5)
                v_res = await session.execute(v_stmt)
                vocab_words = [item.word for item in v_res.scalars().all()]
            except:
                pass
            break

    persona = PERSONA_PROMPTS.get(user.get("tutor_persona") or "friendly")
    cefr = user.get("cefr_level", "A1")
    goals = user.get("goals", [])

    return "\n".join(
        [
            f"Native language: {user.get('native_language')}",
            f"Target language: {user.get('target_language')}",
            f"CEFR level: {cefr}. {CEFR_RULES.get(cefr, '')}",
            f"Persona: {persona}",
            f"Goals: {', '.join(goals) if isinstance(goals, list) else goals}",
            f"Grammar weaknesses: {', '.join(grammar_rules)}",
            f"Inject learning words: {', '.join(vocab_words)}",
            "Rules: respond only in target language, bold new words, end with a question, "
            "correct errors gently, provide explanations in native language when correcting.",
        ]
    )

async def log_llm_error(message: str, metadata: dict) -> None:
    async for session in get_session():
        try:
            log = AdminLog(
                event_type="llm_error",
                message=message,
                metadata_json=metadata,
                admin_id=None,
                user_id=metadata.get("user_id"),
                created_at=datetime.utcnow(),
            )
            session.add(log)
            await session.commit()
        except: pass
        break

async def call_groq(messages: list[dict], system_prompt: str, stream: bool = False) -> str:
    if not settings.GROQ_API_KEY:
        if settings.ENVIRONMENT == "test": return "Mock Groq Response"
        raise RuntimeError("Groq API key not configured")

    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 500,
        "temperature": 0.7,
        "stream": stream,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
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
    if not settings.GEMINI_API_KEY:
        if settings.ENVIRONMENT == "test": return "Mock Gemini Response"
        raise RuntimeError("Gemini API key not configured")
    
    contents = []
    contents.append({"role": "user", "parts": [{"text": system_prompt}]})
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 500}
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
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
        await log_llm_error("Groq failed", {"user_id": user.get("id") or user.get("_id"), "error": str(exc)})
        return await call_gemini(messages, system_prompt)
