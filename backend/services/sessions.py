from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from ..database import active_sessions_collection


async def invalidate_session(user_id: ObjectId) -> None:
    await active_sessions_collection().update_one(
        {"user_id": user_id, "is_valid": True},
        {"$set": {"is_valid": False}},
    )


async def create_session(user_id: ObjectId, jti: str, device_info: str | None, ip_address: str | None) -> None:
    now = datetime.now(timezone.utc)
    await active_sessions_collection().update_one(
        {"user_id": user_id, "is_valid": True},
        {"$set": {"is_valid": False}},
    )
    await active_sessions_collection().update_one(
        {"user_id": user_id},
        {
            "$set": {
                "session_token_id": jti,
                "device_info": device_info,
                "ip_address": ip_address,
                "created_at": now,
                "last_active": now,
                "is_valid": True,
            }
        },
        upsert=True,
    )


async def validate_session(user_id: ObjectId, jti: str) -> bool:
    session = await active_sessions_collection().find_one(
        {"user_id": user_id, "session_token_id": jti, "is_valid": True}
    )
    if not session:
        return False
    await active_sessions_collection().update_one(
        {"_id": session["_id"]},
        {"$set": {"last_active": datetime.now(timezone.utc)}},
    )
    return True
