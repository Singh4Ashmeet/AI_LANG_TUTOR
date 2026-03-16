from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..config import settings
from ..database import (
    sessions_collection,
    stories_collection,
    users_collection,
    vocabulary_collection,
)
from ..dependencies import get_current_user
from ..services.agents import call_lesson_architect
from ..services.learner import update_streak

router = APIRouter(prefix="/bonus", tags=["bonus"])


class StoryCompleteRequest(BaseModel):
    answers: list[str] | None = None


class SpeedRoundSubmitRequest(BaseModel):
    score: int
    total: int


class ListeningSubmitRequest(BaseModel):
    text: str


class VocabSubmitRequest(BaseModel):
    correct_ids: list[str]


@router.get("/stories")
async def list_stories(user=Depends(get_current_user)):
    # Simple placeholder logic for stories
    # In a real app, this would query generated stories
    return {"items": []}


@router.post("/stories/{story_id}/complete")
async def complete_story(story_id: str, payload: StoryCompleteRequest, user=Depends(get_current_user)):
    # Placeholder
    return {"xp": 50}


@router.get("/speed-round/start")
async def speed_round_start(user=Depends(get_current_user)):
    # Fetch random words to test
    pipeline = [{"$sample": {"size": 10}}]
    cursor = vocabulary_collection().aggregate(pipeline)
    questions = []
    async for doc in cursor:
        questions.append({
            "id": str(doc["_id"]),
            "word": doc.get("word"),
            "translation": doc.get("translation"),
            "options": ["Option A", "Option B", "Option C"]  # Simplified for speed
        })
    
    return {
        "round_id": uuid4().hex,
        "duration_seconds": 60,
        "questions": questions
    }


@router.post("/speed-round/complete")
async def speed_round_complete(payload: SpeedRoundSubmitRequest, user=Depends(get_current_user)):
    earned_xp = payload.score * 2  # 2 XP per correct answer
    
    await sessions_collection().insert_one({
        "user_id": user["_id"],
        "session_type": "speed_round",
        "score": payload.score,
        "total": payload.total,
        "xp_earned": earned_xp,
        "started_at": datetime.now(timezone.utc),
        "ended_at": datetime.now(timezone.utc),
    })

    updated_user = await users_collection().find_one({"_id": user["_id"]})
    updated_user = update_streak(updated_user)
    updated_user["xp"] = int(updated_user.get("xp", 0)) + earned_xp
    updated_user["gems"] = int(updated_user.get("gems", 0)) + (5 if payload.score >= 8 else 1)
    
    # Pop _id before update
    updated_user.pop("_id", None)
    await users_collection().update_one({"_id": user["_id"]}, {"$set": updated_user})
    
    return {"xp": earned_xp, "gems": 5 if payload.score >= 8 else 1}


@router.get("/listening/{item_id}")
async def listening_item(item_id: str, user=Depends(get_current_user)):
    # Mocking a listening exercise
    return {
        "id": item_id,
        "prompt": "Listen and type what you hear",
        "audio_url": "/mock-audio.mp3", # In real app, this would be a TTS blob
        "correct_text": "Hello world"
    }


@router.post("/listening/{item_id}/submit")
async def listening_submit(item_id: str, payload: ListeningSubmitRequest, user=Depends(get_current_user)):
    # Simplified check
    is_correct = len(payload.text) > 3
    earned = 15 if is_correct else 2
    
    await sessions_collection().insert_one({
        "user_id": user["_id"],
        "session_type": "listening",
        "item_id": item_id,
        "user_text": payload.text,
        "is_correct": is_correct,
        "xp_earned": earned,
        "started_at": datetime.now(timezone.utc),
        "ended_at": datetime.now(timezone.utc),
    })

    await users_collection().update_one(
        {"_id": user["_id"]},
        {"$inc": {"xp": earned}}
    )
    
    return {"correct": is_correct, "xp": earned}


@router.get("/vocab-challenge/today")
async def vocab_today(user=Depends(get_current_user)):
    # Fetch learning words
    cursor = vocabulary_collection().find({"user_id": user["_id"], "status": "learning"}).limit(10)
    questions = []
    async for doc in cursor:
        questions.append({
            "id": str(doc["_id"]),
            "word": doc.get("word"),
            "translation": doc.get("translation")
        })
    return {"challenge_id": uuid4().hex, "time_limit": 120, "questions": questions}


@router.post("/vocab-challenge/submit")
async def vocab_submit(payload: VocabSubmitRequest, user=Depends(get_current_user)):
    earned = len(payload.correct_ids) * 5
    
    # Update word status to 'known' for correct answers
    if payload.correct_ids:
        await vocabulary_collection().update_many(
            {"_id": {"$in": [ObjectId(i) for i in payload.correct_ids]}, "user_id": user["_id"]},
            {"$set": {"status": "known", "next_review": datetime.now(timezone.utc)}}
        )

    await sessions_collection().insert_one({
        "user_id": user["_id"],
        "session_type": "vocab_challenge",
        "score": len(payload.correct_ids),
        "xp_earned": earned,
        "started_at": datetime.now(timezone.utc),
        "ended_at": datetime.now(timezone.utc),
    })
    
    await users_collection().update_one(
        {"_id": user["_id"]},
        {"$inc": {"xp": earned, "gems": 10}}
    )
    
    return {"xp": earned, "gems": 10}
