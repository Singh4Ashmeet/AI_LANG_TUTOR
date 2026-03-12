from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from ..database import leaderboard_entries_collection, users_collection
from ..dependencies import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _week_start(now: datetime) -> datetime:
    weekday = now.weekday()
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=weekday)
    return start


@router.get("/weekly")
async def weekly_leaderboard(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    week_start = _week_start(now)
    existing = await leaderboard_entries_collection().count_documents({"week_start": week_start})
    if existing == 0:
        cursor = users_collection().find({}).sort("weekly_xp", -1).limit(100)
        rank = 1
        async for entry in cursor:
            await leaderboard_entries_collection().insert_one(
                {
                    "user_id": entry["_id"],
                    "username": entry.get("username"),
                    "avatar_color": entry.get("avatar_color"),
                    "weekly_xp": entry.get("weekly_xp", 0),
                    "week_start": week_start,
                    "rank": rank,
                }
            )
            rank += 1
    cursor = leaderboard_entries_collection().find({"week_start": week_start}).sort("rank", 1)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        items.append(item)
    return {"items": items, "week_start": week_start}


@router.get("/friends")
async def friends_leaderboard(user=Depends(get_current_user)):
    friend_ids = user.get("friends", [])
    cursor = users_collection().find({"_id": {"$in": friend_ids}}).sort("weekly_xp", -1)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        items.append(
            {
                "user_id": item["_id"],
                "username": item.get("username"),
                "weekly_xp": item.get("weekly_xp", 0),
                "avatar_color": item.get("avatar_color"),
            }
        )
    return {"items": items}
