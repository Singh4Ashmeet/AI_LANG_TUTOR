from __future__ import annotations
import json
from datetime import datetime, timezone
import httpx
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import settings
from ..models.admin import AdminLog
from ..models.vocabulary import VocabularyItem
from ..models.extra import GrammarStat
from ..database import get_session

# Helper to get a session for internal logging if one isn't provided
# In a real app, you'd want to pass the session down, but for background logging 
# or error handling, we might need a fresh one.
# For now, we will change _log_agent_error to accept a session or create one.

async def _log_agent_error(agent: str, message: str, metadata: dict | None = None) -> None:
    # We need a session to log errors. Since this is often called in exception handlers
    # where we might not have the session readily available or it might be rolled back,
    # we'll use a new session.
    async for session in get_session():
        try:
            log = AdminLog(
                event_type="llm_error",
                message=f"{agent}: {message}",
                metadata_json=metadata or {},
                admin_id=None,
                user_id=metadata.get("user_id") if metadata else None,
                created_at=datetime.utcnow(),
            )
            session.add(log)
            await session.commit()
        except Exception:
            pass # Failsafe
        break # Only need one yield from get_session

async def _call_groq(messages: list[dict], system_prompt: str, temperature: float, max_tokens: int) -> str:
    if not settings.GROQ_API_KEY:
        # Fallback to mock if no key (for testing) or raise
        if settings.ENVIRONMENT == "test": return '{"mock": "response"}'
        raise RuntimeError("Groq API key not configured")
        
    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

async def _call_gemini(messages: list[dict], system_prompt: str, temperature: float, max_tokens: int) -> str:
    if not settings.GEMINI_API_KEY:
         if settings.ENVIRONMENT == "test": return '{"mock": "response"}'
         raise RuntimeError("Gemini API key not configured")
         
    # Gemini 1.5 format is different, simplified here
    contents = []
    contents.append({"role": "user", "parts": [{"text": system_prompt}]}) # System prompt as first user msg often works better for Gemini if sys prompt not supported directly in this endpoint version
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
        
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
    }
    
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

def _extract_json(text: str) -> dict | list | None:
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
        
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
    start = min([pos for pos in (text.find("{"), text.find("[")) if pos != -1], default=-1)
    end = max(text.rfind("}"), text.rfind("]"))
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None

def _conversation_prompt(user_context: dict, grammar_rules: list[str], vocab_words: list[str]) -> str:
    # Safely handle user_context whether it's a dict or object (it's passed as dict mostly)
    persona = user_context.get("tutor_persona") or "friendly"
    tutor_name = user_context.get("tutor_name") or "Sofia"
    goals = user_context.get("goals", [])
    
    return "\n".join(
        [
            f"You are {tutor_name}, a language tutor persona.",
            f"Native language: {user_context.get('native_language')}",
            f"Target language: {user_context.get('target_language')}",
            f"CEFR level: {user_context.get('cefr_level', 'A1')}",
            f"Persona style: {persona}",
            f"Goals: {', '.join(goals) if isinstance(goals, list) else goals}",
            f"Grammar weaknesses: {', '.join(grammar_rules)}",
            f"Target vocabulary: {', '.join(vocab_words)}",
            "Stay in character as the tutor persona. Never discuss anything outside language learning.",
        ]
    )

# Note: This function now requires a session!
async def _get_grammar_vocab(session: AsyncSession, user_id: int) -> tuple[list[str], list[str]]:
    # Get weak grammar rules
    g_stmt = select(GrammarStat).where(GrammarStat.user_id == user_id).order_by(GrammarStat.errors.desc()).limit(3)
    g_result = await session.execute(g_stmt)
    grammar = g_result.scalars().all()
    
    # Get learning vocabulary
    v_stmt = select(VocabularyItem).where(VocabularyItem.user_id == user_id, VocabularyItem.status == "learning").limit(5)
    v_result = await session.execute(v_stmt)
    vocab = v_result.scalars().all()
    
    return [item.rule for item in grammar], [item.word for item in vocab]

# Updated to accept optional session, but most calls currently don't pass it.
# We'll use a fresh session for _get_grammar_vocab if needed, or refactor caller.
# For simplicity in this migration step, we'll create a local session context for _get_grammar_vocab
async def _fetch_context_data(user_context: dict) -> tuple[list[str], list[str]]:
    user_id = user_context.get("id") or user_context.get("_id")
    # Handle ObjectId string if passed
    try:
        if isinstance(user_id, str) and not user_id.isdigit():
             # Fallback if we still have some old IDs floating, but shouldn't happen
             return [], []
        user_id = int(user_id)
    except (ValueError, TypeError):
        return [], []
        
    async for session in get_session():
        try:
            return await _get_grammar_vocab(session, user_id)
        except Exception:
            return [], []
        # No commit needed, just read
    return [], []

async def call_lesson_architect(messages: list[dict], user_context: dict) -> dict | str:
    system_prompt = (
        "You are a professional language curriculum designer. "
        "Always return valid JSON only. No markdown. "
        "Follow the exact JSON schema provided in each request."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.3, 2000)
    except Exception as exc:
        await _log_agent_error("lesson_architect", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
            text = await _call_gemini(messages, system_prompt, 0.3, 2000)
        except Exception:
            return {} # Fallback
            
    parsed = _extract_json(text)
    return parsed if parsed is not None else text

async def call_conversation_tutor(messages: list[dict], user_context: dict) -> str:
    grammar_rules, vocab_words = await _fetch_context_data(user_context)
    system_prompt = _conversation_prompt(user_context, grammar_rules, vocab_words)
    try:
        return await _call_groq(messages, system_prompt, 0.75, 400)
    except Exception as exc:
        await _log_agent_error("conversation_tutor", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
            return await _call_gemini(messages, system_prompt, 0.75, 400)
        except Exception:
            return "I'm having trouble connecting right now. Let's try again later."

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
        await _log_agent_error("roleplay_engine", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
            return await _call_gemini(messages, system_prompt, 0.85, 350)
        except Exception:
             return "..."

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
        await _log_agent_error("error_analyst", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
             text = await _call_gemini(messages, system_prompt, 0.1, 600)
        except Exception:
             return {"errors": [], "difficulty_estimate": 0.0, "new_vocabulary": []}
             
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
        await _log_agent_error("progress_evaluator", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
            text = await _call_gemini(messages, system_prompt, 0.2, 500)
        except Exception:
            return {"cefr_level": user_context.get("cefr_level", "A1"), "reasoning": "Service unavailable"}
            
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
        await _log_agent_error("scenario_creator", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
            text = await _call_gemini(messages, system_prompt, 0.9, 800)
        except Exception:
            return {}
            
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
        await _log_agent_error("feedback_coach", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
             return await _call_gemini(messages, system_prompt, 0.6, 300)
        except Exception:
             return "Great job practicing today! Keep it up!"

async def call_story_narrator(messages: list[dict], user_context: dict) -> dict:
    system_prompt = (
        "Generate immersive stories for the Stories bonus activity. "
        "Return story text in target language + comprehension questions as JSON."
    )
    try:
        text = await _call_groq(messages, system_prompt, 0.8, 600)
    except Exception as exc:
        await _log_agent_error("story_narrator", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
            text = await _call_gemini(messages, system_prompt, 0.8, 600)
        except Exception:
            return {}
            
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
        await _log_agent_error("summary_agent", "Groq failed", {"error": str(exc), "user_id": user_context.get("id")})
        try:
             text = await _call_gemini(messages, system_prompt, 0.4, 600)
        except Exception:
             return {}
    parsed = _extract_json(text)
    if isinstance(parsed, dict):
        return parsed
    return {}
