from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from cachetools import TTLCache
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..models.extra import Curriculum

router = APIRouter(prefix="/curriculum", tags=["curriculum"])

# Cache with 1 hour TTL, max 100 entries
_curriculum_cache = TTLCache(maxsize=100, ttl=3600)

def _language_pair(user: User) -> str:
    return f"{user.native_language or 'en'}-{user.target_language or 'es'}"

@router.get("")
async def get_curriculum(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    pair = _language_pair(user)
    if pair in _curriculum_cache:
        return _curriculum_cache[pair]
    
    statement = select(Curriculum).where(Curriculum.language_pair == pair)
    result = await session.execute(statement)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Convert to dict for cache and return
        data = existing.model_dump()
        data["id"] = existing.id
        _curriculum_cache[pair] = data
        return data
    
    raise HTTPException(status_code=404, detail="Curriculum not found. Please contact support.")

@router.get("/skill/{skill_id}")
async def get_skill(
    skill_id: str, 
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    curriculum = await get_curriculum(user, session)
    try:
        sid = int(skill_id)
        for section in curriculum.get("sections", []):
            for skill in section.get("skills", []):
                if int(skill.get("skill_id", -1)) == sid:
                    return {
                        "skill": skill,
                        "section": section,
                        "tip_cards": skill.get("tip_cards", []),
                        "lesson_count": 5,
                    }
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Skill not found")
