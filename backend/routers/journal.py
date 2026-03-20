from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..models.session import Session
from ..services.agents import call_feedback_coach

router = APIRouter(prefix="/journal", tags=["journal"])


class JournalRequest(BaseModel):
    text: str


@router.get("")
async def list_journal(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    statement = select(Session).where(
        Session.user_id == user.id, 
        Session.session_type == "journal"
    ).order_by(desc(Session.started_at))
    
    result = await db.execute(statement)
    items = result.scalars().all()
    return {"items": items}


@router.post("")
async def create_journal(
    payload: JournalRequest, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    now = datetime.utcnow()
    message = {
        "role": "user", 
        "content": payload.text, 
        "timestamp": now.isoformat(), 
        "errors": [], 
        "new_vocabulary": []
    }
    
    new_session = Session(
        user_id=user.id,
        session_type="journal",
        messages=[message],
        xp_earned=60,
        started_at=now,
        ended_at=now,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    user_dict = user.model_dump()
    feedback = await call_feedback_coach(
        [{"role": "user", "content": payload.text}],
        user_dict,
    )
    
    new_session.coach_tip = feedback
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return {"id": new_session.id, "feedback": feedback, "xp": 60}


@router.get("/{journal_id}")
async def get_journal(
    journal_id: int, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    statement = select(Session).where(
        Session.id == journal_id, 
        Session.user_id == user.id, 
        Session.session_type == "journal"
    )
    result = await db.execute(statement)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    
    return item
