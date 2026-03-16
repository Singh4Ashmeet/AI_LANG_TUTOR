from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from ..config import settings
from ..database import admin_logs_collection, grammar_stats_collection, vocabulary_collection


async def _log_agent_error(agent: str, message: str, metadata: dict | None = None) -> None:
    await admin_logs_collection().insert_one(
        {
            "event_type": "llm_error",
            "message": f"{agent}: {message}",
            "metadata": metadata or {},
            "admin_id": None,
            "user_id": metadata.get("user_id") if metadata else None,
            "created_at": datetime.now(timezone.utc),
        }
    )


async def _call_groq(messages: list[dict], system_prompt: str, temperature: float, max_tokens: int) -> str:
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key not configured")
    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_gemini(messages: list[dict], system_prompt: str, temperature: float, max_tokens: int) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("Gemini API key not configured")
    text = json.dumps(
        {
            "system": system_prompt,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    )
    payload = {"contents": [{"parts": [{"text": text}]}]}
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


def _extract_json(text: str) -> dict | list | None:
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    start = min([pos for pos in (text.find("{"), text.find("[")) if pos != -1], default=-1)
    end = max(text.rfind("}"), text.rfind("]"))
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def _conversation_prompt(user: dict, grammar_rules: list[str], vocab_words: list[str]) -> str:
    persona = user.get("tutor_persona") or "friendly"
    tutor_name = user.get("tutor_name") or "Sofia"
    return "\n".join(
        [
            f"You are {tutor_name}, a language tutor persona.",
            f"Native language: {user.get('native_language')}",
            f"Target language: {user.get('target_language')}",
            f"CEFR level: {user.get('cefr_level', 'A1')}",
            f"Persona style: {persona}",
            f"Goals: {', '.join(user.get('goals', []))}",
            f"Grammar weaknesses: {', '.join(grammar_rules)}",
            f"Target vocabulary: {', '.join(vocab_words)}",
            "Stay in character as the tutor persona. Never discuss anything outside language learning.",
        ]
    )


async def _get_grammar_vocab(user: dict) -> tuple[list[str], list[str]]:
    grammar = await grammar_stats_collection().find({"user_id": user["_id"], "mastery": {"$lt": 0.5}}).sort("mastery", 1).to_list(length=3)
    vocab = await vocabulary_collection().find({"user_id": user["_id"], "status": "learning"}).to_list(length=5)
    return [item.get("rule") for item in grammar], [item.get("word") for item in vocab]


async def call_lesson_architect(messages: list[dict], user_context: dict) -> dict | str:
    system_prompt = (
        "You are a professional language curriculum designer. "
        "Always return valid JSON only. No markdown. "
        "Follow the exact JSON schema provided in each request."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.3, 2000)
    except Exception as exc:
        await _log_agent_error("lesson_architect", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        text = await _call_gemini(messages, system_prompt, 0.3, 2000)
    parsed = _extract_json(text)
    return parsed if parsed is not None else text


async def call_conversation_tutor(messages: list[dict], user_context: dict) -> str:
    grammar_rules, vocab_words = await _get_grammar_vocab(user_context)
    system_prompt = _conversation_prompt(user_context, grammar_rules, vocab_words)
    try:
        return await _call_groq(messages, system_prompt, 0.75, 400)
    except Exception as exc:
        await _log_agent_error("conversation_tutor", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        return await _call_gemini(messages, system_prompt, 0.75, 400)


async def call_roleplay_engine(messages: list[dict], user_context: dict) -> str:
    role = user_context.get("role") or "NPC"
    scenario = user_context.get("scenario") or "roleplay"
    target_language = user_context.get("target_language")
    native_language = user_context.get("native_language")
    system_prompt = (
        f"You are playing the character of {role} in {scenario}. "
        f"Stay fully in character. Respond only in {target_language}. "
        "You are NOT a language tutor — you are a real person in this situation. "
        f"At the end of your message ONLY, append: (Correction: [if error, explain briefly in {native_language}; if none, write 'Great!'])"
    )
    try:
        return await _call_groq(messages, system_prompt, 0.85, 350)
    except Exception as exc:
        await _log_agent_error("roleplay_engine", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        return await _call_gemini(messages, system_prompt, 0.85, 350)


async def call_error_analyst(messages: list[dict], user_context: dict) -> dict:
    system_prompt = (
        "You are a precise grammar and vocabulary error analyzer. "
        f"Given a message in {user_context.get('target_language')} from a {user_context.get('cefr_level', 'A1')} student whose native "
        f"language is {user_context.get('native_language')}, identify all errors. "
        "Return ONLY valid JSON. Never return anything outside the JSON structure."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.1, 600)
    except Exception as exc:
        await _log_agent_error("error_analyst", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        text = await _call_gemini(messages, system_prompt, 0.1, 600)
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return {"errors": [], "difficulty_estimate": 0.0, "new_vocabulary": []}


async def call_progress_evaluator(messages: list[dict], user_context: dict) -> dict:
    system_prompt = (
        "You are a certified language assessment specialist. "
        "You evaluate conversations against the CEFR framework (A1-C2). "
        "Return structured JSON assessments."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.2, 500)
    except Exception as exc:
        await _log_agent_error("progress_evaluator", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        text = await _call_gemini(messages, system_prompt, 0.2, 500)
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return {"cefr_level": user_context.get("cefr_level", "A1"), "reasoning": ""}


async def call_scenario_creator(messages: list[dict], user_context: dict) -> dict:
    system_prompt = (
        "Create new custom roleplay scenarios on demand. Return ONLY JSON with: "
        "{ title, description, opening_line_in_target_language, suggested_vocabulary, difficulty, skills_practiced }"
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.9, 800)
    except Exception as exc:
        await _log_agent_error("scenario_creator", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        text = await _call_gemini(messages, system_prompt, 0.9, 800)
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return {}


async def call_feedback_coach(messages: list[dict], user_context: dict) -> str:
    system_prompt = (
        "You are an encouraging language learning coach. "
        "Given a learner's session data, write ONE specific, actionable, encouraging tip "
        "in their native language. Keep it under 3 sentences. Be specific to their actual errors."
    )
    try:
        return await _call_groq(messages, system_prompt, 0.6, 300)
    except Exception as exc:
        await _log_agent_error("feedback_coach", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        return await _call_gemini(messages, system_prompt, 0.6, 300)


async def call_story_narrator(messages: list[dict], user_context: dict) -> dict:
    system_prompt = (
        "Generate immersive stories for the Stories bonus activity. "
        "Return story text in target language + comprehension questions as JSON."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.8, 600)
    except Exception as exc:
        await _log_agent_error("story_narrator", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        text = await _call_gemini(messages, system_prompt, 0.8, 600)
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return {}


async def call_summary_agent(messages: list[dict], user_context: dict) -> dict:
    system_prompt = (
        "You are a language tutor summarizing a practice session. "
        "Return JSON: {summary, key_vocabulary_used, grammar_tips}. "
        "Keep the summary encouraging but highlight areas for improvement."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.4, 600)
    except Exception as exc:
        await _log_agent_error("summary_agent", "Groq failed", {"error": str(exc), "user_id": user_context.get("_id")})
        text = await _call_gemini(messages, system_prompt, 0.4, 600)
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return {}
