from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_current_user
from ..services.agents import call_lesson_architect

router = APIRouter(prefix="/grammar", tags=["grammar"])

_grammar_cache: dict[str, dict] = {}


def _pair(user: dict) -> str:
    return f"{user.get('native_language', 'en')}-{user.get('target_language', 'es')}"


@router.get("/guide")
async def grammar_guide(user=Depends(get_current_user)):
    pair = _pair(user)
    if pair in _grammar_cache:
        return _grammar_cache[pair]
    prompt = {
        "role": "user",
        "content": (
            "Generate a complete grammar guide JSON organized by: Verb tenses, Pronouns, Adjectives, Sentence structure. "
            "Each rule should include explanation and 5 examples. Return JSON only."
        ),
    }
    result = await call_lesson_architect([prompt], user)
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Grammar guide generation failed")
    _grammar_cache[pair] = result
    return result


@router.post("/deep-dive/{rule}")
async def deep_dive(rule: str, user=Depends(get_current_user)):
    prompt = {
        "role": "user",
        "content": (
            "Generate 5 targeted exercises for this grammar rule. Return JSON: {rule, exercises:[{type, prompt, content, choices, correct_answer, explanation}]} "
            f"Rule: {rule}."
        ),
    }
    result = await call_lesson_architect([prompt], user)
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Grammar deep dive failed")
    return result
