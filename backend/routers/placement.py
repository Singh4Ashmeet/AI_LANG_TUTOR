from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..models.session import Session
from ..services.agents import call_progress_evaluator

router = APIRouter(prefix="/placement", tags=["placement"])

QUESTIONS = [
    "Hola. Como te llamas? (Hello, what is your name?)",
    "De donde eres? (Where are you from?)",
    "Que haces normalmente en tu dia? (What do you usually do in your day?)",
    "Que hiciste ayer? (What did you do yesterday?)",
    "Que planes tienes para manana? (What plans do you have for tomorrow?)",
    "Describe tu ciudad favorita. (Describe your favorite city.)",
    "Habla de un problema que resolviste. (Talk about a problem you solved.)",
    "Cuentame un recuerdo importante. (Tell me an important memory.)",
]

class PlacementStartResponse(BaseModel):
    session_id: int
    question: str
    index: int

class PlacementAnswerRequest(BaseModel):
    session_id: int
    answer: str
    index: int

class PlacementFinishRequest(BaseModel):
    session_id: int
    cefr_level: str | None = None
    reasoning: str | None = None

@router.get("/start", response_model=PlacementStartResponse)
async def start(
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    now = datetime.utcnow()
    db_session = Session(
        user_id=user.id,
        session_type="placement",
        scenario=None,
        messages=[],
        xp_earned=0,
        duration_seconds=0,
        grammar_errors_count=0,
        vocabulary_added_count=0,
        started_at=now,
        ended_at=None,
    )
    session_db.add(db_session)
    await session_db.commit()
    await session_db.refresh(db_session)
    return {"session_id": db_session.id, "question": QUESTIONS[0], "index": 0}

@router.post("/respond")
async def respond(
    payload: PlacementAnswerRequest, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    stmt = select(Session).where(Session.id == payload.session_id, Session.user_id == user.id)
    result = await session_db.execute(stmt)
    db_session = result.scalar_one_or_none()
    
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    message = {
        "role": "user",
        "content": payload.answer,
        "timestamp": datetime.utcnow().isoformat(),
        "errors": [],
        "new_vocabulary": [],
    }
    db_session.messages.append(message)
    flag_modified(db_session, "messages")
    session_db.add(db_session)
    await session_db.commit()

    next_index = payload.index + 1
    if next_index >= len(QUESTIONS):
        return {"done": True}
    return {"question": QUESTIONS[next_index], "index": next_index}

@router.post("/finish")
async def finish(
    payload: PlacementFinishRequest, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    stmt = select(Session).where(Session.id == payload.session_id, Session.user_id == user.id)
    result = await session_db.execute(stmt)
    db_session = result.scalar_one_or_none()
    
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    transcript = [
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in db_session.messages
    ]
    evaluator_prompt = {
        "role": "user",
        "content": json.dumps({
            "task": "placement_evaluation",
            "conversation": transcript,
            "return_schema": {"cefr_level": "A1", "reasoning": "brief explanation"},
        }),
    }
    # call_progress_evaluator might need dict for user
    eval_result = await call_progress_evaluator([evaluator_prompt], user.model_dump())
    cefr_level = eval_result.get("cefr_level") or payload.cefr_level or "A1"
    reasoning = eval_result.get("reasoning") or payload.reasoning or ""

    user.cefr_level = cefr_level
    # onboarding_complete might need to be added to User model
    # user.onboarding_complete = True 
    
    db_session.ended_at = datetime.utcnow()
    db_session.xp_earned = 100
    
    session_db.add(user)
    session_db.add(db_session)
    await session_db.commit()
    
    return {"cefr_level": cefr_level, "reasoning": reasoning}
