from __future__ import annotations

import json
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, status
from pydantic import BaseModel

from ..database import admin_logs_collection, grammar_stats_collection, sessions_collection, users_collection, vocabulary_collection
from ..dependencies import get_current_user
from ..services.learner import award_xp, update_streak
from ..services.agents import call_conversation_tutor, call_error_analyst, call_feedback_coach, call_summary_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class NewChatResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    message_type: str = "text"


async def _log_admin_event(event_type: str, message: str, user_id: ObjectId | None = None):
    await admin_logs_collection().insert_one(
        {
            "event_type": event_type,
            "message": message,
            "metadata": {},
            "admin_id": None,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
        }
    )


@router.post("/new", response_model=NewChatResponse)
async def new_chat(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    result = await sessions_collection().insert_one(
        {
            "user_id": user["_id"],
            "session_type": "tutor_chat",
            "scenario": None,
            "messages": [],
            "xp_earned": 0,
            "duration_seconds": 0,
            "grammar_errors_count": 0,
            "vocabulary_added_count": 0,
            "started_at": now,
            "ended_at": None,
        }
    )
    return {"session_id": str(result.inserted_id)}


async def _record_errors(user: dict, errors: list[dict]) -> None:
    if not errors:
        return
    now = datetime.now(timezone.utc)
    for error in errors:
        rule = error.get("rule") or "unknown"
        await grammar_stats_collection().update_one(
            {"user_id": user["_id"], "rule": rule, "language": user.get("target_language")},
            {
                "$inc": {"errors": 1, "attempts": 1},
                "$set": {"last_error_at": now},
            },
            upsert=True,
        )


async def _record_vocabulary(user: dict, words: list[str], context_sentence: str) -> None:
    if not words:
        return
    now = datetime.now(timezone.utc)
    for word in words:
        existing = await vocabulary_collection().find_one(
            {"user_id": user["_id"], "word": word, "language": user.get("target_language")}
        )
        if existing:
            await vocabulary_collection().update_one(
                {"_id": existing["_id"]},
                {"$inc": {"times_seen": 1}, "$set": {"last_seen": now}},
            )
            continue
        await vocabulary_collection().insert_one(
            {
                "user_id": user["_id"],
                "word": word,
                "translation": "",
                "language": user.get("target_language"),
                "status": "new",
                "ease_factor": 2.5,
                "interval_days": 1,
                "repetitions": 0,
                "next_review": now,
                "last_seen": now,
                "times_seen": 1,
                "times_correct": 0,
                "context_sentence": context_sentence,
                "source_session_id": None,
                "source_skill": None,
                "created_at": now,
            }
        )


@router.post("")
async def chat(payload: ChatRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(payload.session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Get previous context
    history = session.get("messages", [])[-10:] # Get last 10 messages
    messages = [{"role": item["role"], "content": item["content"]} for item in history]
    messages.append({"role": "user", "content": payload.message})

    # Analyze user message
    analysis = await call_error_analyst([{"role": "user", "content": payload.message}], user)
    errors = analysis.get("errors", [])
    new_vocab = analysis.get("new_vocabulary", [])

    user_message = {
        "role": "user",
        "content": payload.message,
        "timestamp": datetime.now(timezone.utc),
        "errors": errors,
        "new_vocabulary": new_vocab,
    }

    # Generate reply
    reply = await call_conversation_tutor(messages, user)

    assistant_message = {
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.now(timezone.utc),
    }

    # Atomic update to push both messages
    await sessions_collection().update_one(
        {"_id": session["_id"]},
        {"$push": {"messages": {"$each": [user_message, assistant_message]}}},
    )

    # Background tasks
    if errors:
        await _record_errors(user, errors)
    if new_vocab:
        await _record_vocabulary(user, new_vocab, payload.message)

    return {
        "reply": reply,
        "corrections": errors,
        "new_words": new_vocab,
        "xp": {"earned": 0, "total": user.get("xp", 0), "streak": user.get("streak", 0), "leveled_up": False},
    }


@router.post("/end/{session_id}")
async def end_session(session_id: str, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    end_time = datetime.now(timezone.utc)
    # Handle legacy sessions that might not have started_at
    start_time = session.get("started_at") or end_time
    duration = int((end_time - start_time).total_seconds())

    # Generate Summary
    messages = session.get("messages", [])
    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    
    summary_prompt = [
        {"role": "user", "content": f"Summarize this conversation and provide feedback:\n{conversation_text}"}
    ]
    
    summary_data = await call_summary_agent(summary_prompt, user)
    
    # Fallback if AI fails to return dict
    if not isinstance(summary_data, dict):
        summary_data = {
            "summary": "Great conversation practice!",
            "key_vocabulary_used": [],
            "grammar_tips": ["Keep practicing!"]
        }

    updated_user = await users_collection().find_one({"_id": user["_id"]})
    updated_user = update_streak(updated_user)
    earned, leveled_up, new_level = award_xp(updated_user, base=50)
    updated_user["updated_at"] = end_time

    # Pop _id before update
    updated_user.pop("_id", None)
    await users_collection().update_one({"_id": user["_id"]}, {"$set": updated_user})
    
    await sessions_collection().update_one(
        {"_id": session["_id"]}, 
        {
            "$set": {
                "ended_at": end_time, 
                "duration_seconds": duration,
                "xp_earned": earned,
                "summary": summary_data
            }
        }
    )

    return {
        "earned": earned,
        "total": updated_user.get("xp", 0),
        "streak": updated_user.get("streak", 0),
        "leveled_up": leveled_up,
        "cefr_level": new_level,
        "summary": summary_data,
    }


@router.websocket("/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    while True:
        message = await websocket.receive_text()
        try:
            reply = message
        except Exception:
            reply = "AI service temporarily unavailable"
        await websocket.send_text(reply)
