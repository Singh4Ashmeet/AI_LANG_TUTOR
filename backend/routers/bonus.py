from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..database import sessions_collection, stories_collection
from ..dependencies import get_current_user
from ..services.agents import call_story_narrator

router = APIRouter(prefix="/bonus", tags=["bonus"])


class StoryCompleteRequest(BaseModel):
    answers: list[str] | None = None


@router.get("/stories")
async def list_stories(user=Depends(get_current_user)):
    cursor = stories_collection().find({"user_id": user["_id"], "read": {"$ne": True}}).sort("created_at", -1).limit(3)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        items.append(item)
    if items:
        return {"items": items}

    stories = []
    for _ in range(3):
        result = await call_story_narrator(
            [{"role": "user", "content": "Generate a short story with 3 comprehension questions as JSON."}],
            user,
        )
        if isinstance(result, dict):
            story = {
                "user_id": user["_id"],
                "story_id": uuid4().hex,
                "content": result,
                "created_at": datetime.now(timezone.utc),
                "read": False,
            }
            inserted = await stories_collection().insert_one(story)
            story["_id"] = str(inserted.inserted_id)
            stories.append(story)
    return {"items": stories}


@router.post("/stories/{story_id}/complete")
async def complete_story(story_id: str, payload: StoryCompleteRequest, user=Depends(get_current_user)):
    story = await stories_collection().find_one({"story_id": story_id, "user_id": user["_id"]})
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    await stories_collection().update_one({"_id": story["_id"]}, {"$set": {"read": True}})
    await sessions_collection().insert_one(
        {
            "user_id": user["_id"],
            "session_type": "story",
            "scenario": story_id,
            "messages": [],
            "exercises": payload.answers or [],
            "xp_earned": 50,
            "started_at": datetime.now(timezone.utc),
            "ended_at": datetime.now(timezone.utc),
        }
    )
    return {"xp": 50}


@router.get("/speed-round/start")
async def speed_round_start(user=Depends(get_current_user)):
    return {"round_id": uuid4().hex, "duration_seconds": 30}


@router.post("/speed-round/complete")
async def speed_round_complete(user=Depends(get_current_user)):
    return {"xp": 40}


@router.get("/listening/{item_id}")
async def listening_item(item_id: str, user=Depends(get_current_user)):
    return {"id": item_id, "prompt": "Transcribe the audio you hear.", "audio_text": ""}


@router.post("/listening/{item_id}/submit")
async def listening_submit(item_id: str, user=Depends(get_current_user)):
    return {"xp": 50}


@router.get("/vocab-challenge/today")
async def vocab_today(user=Depends(get_current_user)):
    return {"challenge_id": uuid4().hex, "time_limit": 60, "questions": []}


@router.post("/vocab-challenge/submit")
async def vocab_submit(user=Depends(get_current_user)):
    return {"xp": 30}
