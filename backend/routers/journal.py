from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..database import sessions_collection
from ..dependencies import get_current_user
from ..services.agents import call_feedback_coach

router = APIRouter(prefix="/journal", tags=["journal"])


class JournalRequest(BaseModel):
    text: str


@router.get("")
async def list_journal(user=Depends(get_current_user)):
    cursor = sessions_collection().find({"user_id": user["_id"], "session_type": "journal"}).sort("started_at", -1)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        items.append(item)
    return {"items": items}


@router.post("")
async def create_journal(payload: JournalRequest, user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    session_doc = {
        "user_id": user["_id"],
        "session_type": "journal",
        "messages": [{"role": "user", "content": payload.text, "timestamp": now, "errors": [], "new_vocabulary": []}],
        "xp_earned": 60,
        "started_at": now,
        "ended_at": now,
    }
    result = await sessions_collection().insert_one(session_doc)
    feedback = await call_feedback_coach(
        [{"role": "user", "content": payload.text}],
        user,
    )
    await sessions_collection().update_one({"_id": result.inserted_id}, {"$set": {"coach_tip": feedback}})
    return {"id": str(result.inserted_id), "feedback": feedback, "xp": 60}


@router.get("/{journal_id}")
async def get_journal(journal_id: str, user=Depends(get_current_user)):
    item = await sessions_collection().find_one({"_id": ObjectId(journal_id), "user_id": user["_id"], "session_type": "journal"})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    item["_id"] = str(item["_id"])
    item["user_id"] = str(item["user_id"])
    return item
