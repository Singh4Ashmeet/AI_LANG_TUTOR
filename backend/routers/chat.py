from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, status
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from ..database import get_session
from ..dependencies import get_current_user
from ..models.user import User
from ..models.session import Session
from ..models.extra import GrammarStat
from ..models.vocabulary import VocabularyItem
from ..services.learner import award_xp, update_streak
from ..services.agents import call_conversation_tutor, call_error_analyst, call_summary_agent

router = APIRouter(prefix="/chat", tags=["chat"])

class NewChatResponse(BaseModel):
    session_id: int

class ChatRequest(BaseModel):
    session_id: int
    message: str
    message_type: str = "text"

# Helper functions for background tasks need their own session management 
# or must be awaited within the request scope if using the dependency session.
# Since we want to await them in the request to ensure data consistency for now:

async def _record_errors(session: AsyncSession, user: User, errors: list[dict]) -> None:
    if not errors:
        return
    now = datetime.utcnow()
    for error in errors:
        rule = error.get("rule") or "unknown"
        stmt = select(GrammarStat).where(
            GrammarStat.user_id == user.id,
            GrammarStat.rule == rule,
            GrammarStat.language == (user.target_language or "es")
        )
        result = await session.execute(stmt)
        stat = result.scalar_one_or_none()
        
        if stat:
            stat.errors += 1
            stat.attempts += 1
            stat.last_error_at = now
            session.add(stat)
        else:
            new_stat = GrammarStat(
                user_id=user.id,
                rule=rule,
                language=(user.target_language or "es"),
                errors=1,
                attempts=1,
                last_error_at=now
            )
            session.add(new_stat)

async def _record_vocabulary(session: AsyncSession, user: User, words: list[str], context_sentence: str) -> None:
    if not words:
        return
    now = datetime.utcnow()
    for word in words:
        stmt = select(VocabularyItem).where(
            VocabularyItem.user_id == user.id,
            VocabularyItem.word == word,
            VocabularyItem.language == (user.target_language or "es")
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.times_seen = (existing.times_seen or 0) + 1
            existing.last_seen = now
            session.add(existing)
        else:
            new_vocab = VocabularyItem(
                user_id=user.id,
                word=word,
                translation="",
                language=(user.target_language or "es"),
                status="new",
                ease_factor=2.5,
                interval_days=1,
                repetitions=0,
                next_review=now,
                last_seen=now,
                times_seen=1,
                times_correct=0,
                context_sentence=context_sentence,
                created_at=now,
            )
            session.add(new_vocab)

@router.post("/new", response_model=NewChatResponse)
async def new_chat(
    user: User = Depends(get_current_user), 
    session_db: AsyncSession = Depends(get_session)
):
    now = datetime.utcnow()
    # Default opening message
    opening = "Hola! Soy Sofia. De que quieres hablar hoy?"
    
    new_session = Session(
        user_id=user.id,
        session_type="tutor_chat",
        messages=[{
            "role": "assistant", 
            "content": opening, 
            "timestamp": now.isoformat()
        }],
        xp_earned=0,
        started_at=now,
    )
    session_db.add(new_session)
    await session_db.commit()
    await session_db.refresh(new_session)
    return {"session_id": new_session.id}

@router.post("")
async def chat(
    payload: ChatRequest, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    stmt = select(Session).where(Session.id == payload.session_id, Session.user_id == user.id)
    result = await session_db.execute(stmt)
    chat_session = result.scalar_one_or_none()
    
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Analyze user message
    user_dict = user.model_dump()
    try:
        analysis = await call_error_analyst([{"role": "user", "content": payload.message}], user_dict)
    except Exception:
        analysis = {"errors": [], "new_vocabulary": []}
        
    errors = analysis.get("errors", [])
    new_vocab = analysis.get("new_vocabulary", [])

    # Record stats (awaiting here to keep session open)
    await _record_errors(session_db, user, errors)
    await _record_vocabulary(session_db, user, new_vocab, payload.message)

    user_message = {
        "role": "user",
        "content": payload.message,
        "timestamp": datetime.utcnow().isoformat(),
        "errors": errors,
        "new_vocabulary": new_vocab,
    }
    
    # Append to messages
    chat_session.messages.append(user_message)
    flag_modified(chat_session, "messages")
    session_db.add(chat_session)
    await session_db.commit() # Commit user msg first

    # Prepare context for AI
    history = chat_session.messages[-10:] if chat_session.messages else []
    ai_messages = [{"role": m["role"], "content": m["content"]} for m in history]

    # Generate reply
    reply = await call_conversation_tutor(ai_messages, user_dict)

    assistant_message = {
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.utcnow().isoformat(),
    }

    chat_session.messages.append(assistant_message)
    flag_modified(chat_session, "messages")
    session_db.add(chat_session)
    await session_db.commit()

    return {
        "reply": reply,
        "corrections": errors,
        "new_words": new_vocab,
    }

@router.post("/end/{session_id}")
async def end_session(
    session_id: int, 
    user: User = Depends(get_current_user),
    session_db: AsyncSession = Depends(get_session)
):
    stmt = select(Session).where(Session.id == session_id, Session.user_id == user.id)
    result = await session_db.execute(stmt)
    chat_session = result.scalar_one_or_none()
    
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    end_time = datetime.utcnow()
    duration = int((end_time - chat_session.started_at).total_seconds())

    # Generate Summary
    messages = chat_session.messages or []
    # Simplified summary prompt
    conversation_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
    summary_prompt = [{"role": "user", "content": f"Summarize:\n{conversation_text}"}]
    
    user_dict = user.model_dump()
    summary_data = await call_summary_agent(summary_prompt, user_dict)
    
    # Update stats
    update_streak(user) # Updates user object in place
    earned, leveled_up, new_level = award_xp(user, base=50)
    
    chat_session.ended_at = end_time
    chat_session.duration_seconds = duration
    chat_session.xp_earned = earned
    chat_session.summary = summary_data
    
    session_db.add(user)
    session_db.add(chat_session)
    await session_db.commit()

    return {
        "earned": earned,
        "total": user.xp,
        "streak": user.streak,
        "leveled_up": leveled_up,
        "cefr_level": new_level,
        "summary": summary_data,
    }

@router.websocket("/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    while True:
        message = await websocket.receive_text()
        await websocket.send_text("Streaming not implemented yet")
