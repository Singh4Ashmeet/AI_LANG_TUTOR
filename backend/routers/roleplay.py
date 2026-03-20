from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4
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
from ..models.vocabulary import VocabularyItem
from ..models.extra import GrammarStat
from ..services.learner import award_xp, update_streak
from ..services.agents import call_error_analyst, call_feedback_coach, call_roleplay_engine, call_scenario_creator

router = APIRouter(prefix="/roleplay", tags=["roleplay"])

SCENARIOS = [
    {
        "id": "restaurant",
        "name": "Restaurant",
        "difficulty": "A1",
        "description": "Order food, ask questions, and pay the bill.",
        "skills": ["ordering", "polite requests", "numbers"],
        "ai_role": "Waiter",
        "opening": "Bienvenido. Tiene una reservacion?",
    },
    {
        "id": "airport",
        "name": "Airport",
        "difficulty": "A2",
        "description": "Check in and handle a flight issue.",
        "skills": ["travel", "problem solving", "polite requests"],
        "ai_role": "Check-in agent",
        "opening": "Buenos dias. Puede mostrar su pasaporte?",
    },
    {
        "id": "job_interview",
        "name": "Job Interview",
        "difficulty": "B1",
        "description": "Answer professional questions and discuss experience.",
        "skills": ["career", "self introduction", "past tense"],
        "ai_role": "Interviewer",
        "opening": "Hola. Puede contarme sobre su experiencia reciente?",
    },
    {
        "id": "doctor",
        "name": "Doctor Visit",
        "difficulty": "B1",
        "description": "Describe symptoms and understand advice.",
        "skills": ["health", "describing symptoms", "listening"],
        "ai_role": "Doctor",
        "opening": "Hola. Que le duele hoy?",
    },
    {
        "id": "market",
        "name": "Street Market",
        "difficulty": "A2",
        "description": "Browse, negotiate, and buy something.",
        "skills": ["shopping", "numbers", "bargaining"],
        "ai_role": "Vendor",
        "opening": "Buenos dias. Busca algo especial?",
    },
    {
        "id": "first_date",
        "name": "First Date",
        "difficulty": "B2",
        "description": "Casual conversation about opinions and interests.",
        "skills": ["opinions", "humor", "small talk"],
        "ai_role": "Date",
        "opening": "Hola. Como estuvo tu dia?",
    },
    {
        "id": "hotel",
        "name": "Hotel",
        "difficulty": "A2",
        "description": "Check in and handle a room issue.",
        "skills": ["travel", "requests", "polite tone"],
        "ai_role": "Receptionist",
        "opening": "Bienvenido al hotel. Tiene una reserva?",
    },
    {
        "id": "phone_call",
        "name": "Phone Call",
        "difficulty": "B2",
        "description": "Communicate clearly without visual cues.",
        "skills": ["clarification", "listening", "repetition"],
        "ai_role": "Caller",
        "opening": "Hola, soy Alex. Me escucha bien?",
    },
]

class RoleplayNewRequest(BaseModel):
    scenario_id: str | None = None
    scenario: str | None = None

class RoleplayChatRequest(BaseModel):
    session_id: int
    message: str

class RoleplayCustomRequest(BaseModel):
    prompt: str

@router.get("/scenarios")
async def list_scenarios():
    return SCENARIOS

@router.post("/new")
async def start_roleplay(
    payload: RoleplayNewRequest, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    lookup = (payload.scenario_id or payload.scenario or "").strip().lower()
    aliases = {
        "interview": "job_interview",
        "shopping": "market",
        "landlord": "hotel",
        "coffee": "first_date",
    }
    lookup = aliases.get(lookup, lookup)
    scenario = next(
        (s for s in SCENARIOS if s["id"].lower() == lookup or s["name"].lower() == lookup),
        None,
    )
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    now = datetime.utcnow()
    db_session = Session(
        user_id=user.id,
        session_type="roleplay",
        scenario=scenario["id"],
        messages=[
            {
                "role": "assistant",
                "content": scenario["opening"],
                "timestamp": now.isoformat(),
                "errors": [],
                "new_vocabulary": [],
            }
        ],
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
    return {"session_id": db_session.id, "opening": scenario["opening"]}


@router.post("/custom")
async def start_custom_roleplay(
    payload: RoleplayCustomRequest,
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session),
):
    generated = await call_scenario_creator(
        [{"role": "user", "content": payload.prompt}],
        user.model_dump(),
    )
    title = generated.get("title") or "Custom Scenario"
    opening = generated.get("opening_line_in_target_language") or "Hola, empecemos."

    now = datetime.utcnow()
    db_session = Session(
        user_id=user.id,
        session_type="roleplay",
        scenario=f"custom:{title}",
        messages=[
            {
                "role": "assistant",
                "content": opening,
                "timestamp": now.isoformat(),
                "errors": [],
                "new_vocabulary": [],
            }
        ],
        started_at=now,
    )
    session_db.add(db_session)
    await session_db.commit()
    await session_db.refresh(db_session)
    return {"session_id": db_session.id, "opening": opening, "scenario": generated}

@router.post("")
async def roleplay_chat(
    payload: RoleplayChatRequest, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    stmt = select(Session).where(Session.id == payload.session_id, Session.user_id == user.id)
    result = await session_db.execute(stmt)
    db_session = result.scalar_one_or_none()
    
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # In a real app, you'd call these agents
    # For now, let's assume they return empty or mock data if failing
    try:
        analysis = await call_error_analyst([{"role": "user", "content": payload.message}], user)
    except Exception:
        analysis = {"errors": [], "new_vocabulary": []}
        
    errors = analysis.get("errors", [])
    new_vocab = analysis.get("new_vocabulary", [])

    now = datetime.utcnow()
    for error in errors:
        rule = error.get("rule") or "unknown"
        # Update grammar stats
        gs_stmt = select(GrammarStat).where(
            GrammarStat.user_id == user.id, 
            GrammarStat.rule == rule, 
            GrammarStat.language == (user.target_language or "es")
        )
        gs_result = await session_db.execute(gs_stmt)
        gs = gs_result.scalar_one_or_none()
        if gs:
            gs.errors += 1
            gs.attempts += 1
            gs.last_error_at = now
            session_db.add(gs)
        else:
            gs = GrammarStat(
                user_id=user.id,
                rule=rule,
                language=(user.target_language or "es"),
                errors=1,
                attempts=1,
                last_error_at=now
            )
            session_db.add(gs)
            
    for word in new_vocab:
        v_stmt = select(VocabularyItem).where(
            VocabularyItem.user_id == user.id, 
            VocabularyItem.word == word, 
            VocabularyItem.language == (user.target_language or "es")
        )
        v_result = await session_db.execute(v_stmt)
        existing = v_result.scalar_one_or_none()
        if existing:
            existing.times_seen = (existing.times_seen or 0) + 1
            existing.last_seen = now
            session_db.add(existing)
        else:
            vocab_item = VocabularyItem(
                user_id=user.id,
                word=word,
                translation="",
                language=(user.target_language or "es"),
                status="new",
                next_review=now,
                last_seen=now,
                times_seen=1,
                context_sentence=payload.message,
                created_at=now,
            )
            session_db.add(vocab_item)

    user_message = {
        "role": "user",
        "content": payload.message,
        "timestamp": datetime.utcnow().isoformat(),
        "errors": errors,
        "new_vocabulary": new_vocab,
    }
    db_session.messages.append(user_message)
    flag_modified(db_session, "messages")
    session_db.add(db_session)
    await session_db.commit()

    scenario = next((s for s in SCENARIOS if s["id"] == db_session.scenario), None)
    # call_roleplay_engine might need dict for user
    reply = await call_roleplay_engine([{"role": "user", "content": payload.message}], user.model_dump())

    assistant_message = {
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.utcnow().isoformat(),
        "errors": [],
        "new_vocabulary": [],
    }
    db_session.messages.append(assistant_message)
    flag_modified(db_session, "messages")
    session_db.add(db_session)
    await session_db.commit()
    
    return {"reply": reply, "corrections": errors, "new_words": new_vocab}

@router.post("/end/{session_id}")
async def end_roleplay(
    session_id: int, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    stmt = select(Session).where(Session.id == session_id, Session.user_id == user.id)
    result = await session_db.execute(stmt)
    db_session = result.scalar_one_or_none()
    
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    end_time = datetime.utcnow()
    duration = int((end_time - db_session.started_at).total_seconds())
    db_session.ended_at = end_time
    db_session.duration_seconds = duration
    
    user = update_streak(user)
    earned, leveled_up, new_level = award_xp(user, base=80)
    
    summary_prompt = {
        "role": "user",
        "content": json.dumps({
            "session_type": "roleplay",
            "messages": db_session.messages,
        }),
    }
    coach_tip = await call_feedback_coach([summary_prompt], user.model_dump())
    
    db_session.xp_earned = earned
    db_session.coach_tip = coach_tip
    
    session_db.add(db_session)
    session_db.add(user)
    await session_db.commit()

    return {
        "earned": earned,
        "total": user.xp,
        "streak": user.streak,
        "leveled_up": leveled_up,
        "cefr_level": new_level,
        "coach_tip": coach_tip,
    }
