from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import Notification
from ..models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def serialize_notification(item: Notification) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    data["body"] = data.get("message")
    return data


@router.get("")
async def list_notifications(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(Notification).where(Notification.user_id == user.id).order_by(desc(Notification.created_at))
    items = (await session.execute(stmt)).scalars().all()
    return {"items": [serialize_notification(item) for item in items]}


@router.post("/read/{notification_id}")
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    notification = (await session.execute(stmt)).scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.read = True
    session.add(notification)
    await session.commit()
    return {"success": True}


@router.post("/read-all")
async def mark_all_read(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = update(Notification).where(Notification.user_id == user.id, Notification.read == False).values(read=True)
    await session.execute(stmt)
    await session.commit()
    return {"success": True}
