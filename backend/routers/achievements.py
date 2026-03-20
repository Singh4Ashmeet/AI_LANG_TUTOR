from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import Achievement, UserAchievement
from ..models.user import User

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
async def list_achievements(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    items = (await session.execute(select(Achievement))).scalars().all()
    return {"items": [item.model_dump() for item in items]}


@router.get("/earned")
async def earned_achievements(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(UserAchievement).where(UserAchievement.user_id == user.id))).scalars().all()
    ids = [row.achievement_id for row in rows]
    return {"items": ids}

