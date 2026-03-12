from __future__ import annotations

from fastapi import APIRouter, Depends

from ..database import achievements_collection
from ..dependencies import get_current_user

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
async def list_achievements(user=Depends(get_current_user)):
    cursor = achievements_collection().find({})
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        items.append(item)
    return {"items": items}


@router.get("/earned")
async def earned_achievements(user=Depends(get_current_user)):
    return {"items": user.get("achievements_earned", [])}
