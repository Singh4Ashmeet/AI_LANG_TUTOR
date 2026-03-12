from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import curriculum_collection
from ..dependencies import get_current_user
from ..services.agents import call_lesson_architect

router = APIRouter(prefix="/curriculum", tags=["curriculum"])

_curriculum_cache: dict[str, dict] = {}


def _language_pair(user: dict) -> str:
    return f"{user.get('native_language', 'en')}-{user.get('target_language', 'es')}"


async def _generate_curriculum(pair: str, user: dict) -> dict:
    prompt = {
        "role": "user",
        "content": (
            "Generate a curriculum JSON for a language pair with 5 sections and 40-60 skills total. "
            "Each section must include 8-12 skills. Use skill_id as incrementing integers starting at 1. "
            "Return JSON with: {language_pair, sections:[{section_index,title,description,color,emoji,"
            "skills:[{skill_id,title,emoji,description,difficulty,tip_cards:[{title,explanation,examples:[{target,native}]}]}]}]}."
            f" Language pair: {pair}."
        ),
    }
    result = await call_lesson_architect([prompt], user)
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Curriculum generation failed")
    result["language_pair"] = pair
    result["generated_at"] = datetime.now(timezone.utc)
    return result


@router.get("")
async def get_curriculum(user=Depends(get_current_user)):
    pair = _language_pair(user)
    if pair in _curriculum_cache:
        return _curriculum_cache[pair]
    existing = await curriculum_collection().find_one({"language_pair": pair})
    if existing:
        existing["_id"] = str(existing["_id"])
        _curriculum_cache[pair] = existing
        return existing
    generated = await _generate_curriculum(pair, user)
    result = await curriculum_collection().insert_one(generated)
    generated["_id"] = str(result.inserted_id)
    _curriculum_cache[pair] = generated
    return generated


@router.get("/skill/{skill_id}")
async def get_skill(skill_id: str, user=Depends(get_current_user)):
    curriculum = await get_curriculum(user)
    try:
        skill_id_int = int(skill_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid skill id")
    for section in curriculum.get("sections", []):
        for skill in section.get("skills", []):
            if int(skill.get("skill_id", -1)) == skill_id_int:
                return {"skill": skill, "section": {"section_index": section.get("section_index"), "title": section.get("title")}}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
