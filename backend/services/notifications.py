from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.extra import Notification


async def push_notification(
    session: AsyncSession,
    user_id: int,
    title: str,
    message: str,
    kind: str = "info",
) -> Notification:
    item = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=kind,
        read=False,
        created_at=datetime.utcnow(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

