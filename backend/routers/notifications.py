from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import notifications_collection
from ..dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user=Depends(get_current_user)):
    cursor = notifications_collection().find({"user_id": user["_id"]}).sort("created_at", -1)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        items.append(item)
    return {"items": items}


@router.post("/read/{notification_id}")
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    result = await notifications_collection().update_one(
        {"_id": ObjectId(notification_id), "user_id": user["_id"]},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"success": True}


@router.post("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    await notifications_collection().update_many(
        {"user_id": user["_id"], "is_read": {"$ne": True}},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}},
    )
    return {"success": True}
