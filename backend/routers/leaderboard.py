from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import FriendConnection, LeaderboardEntry
from ..models.user import User

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


def _week_start(now: datetime) -> datetime:
    weekday = now.weekday()
    day_start = datetime(now.year, now.month, now.day)
    return day_start - timedelta(days=weekday)


def _serialize_entry(item: LeaderboardEntry) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


async def _refresh_week_entries(session: AsyncSession, week_start: datetime) -> None:
    await session.execute(delete(LeaderboardEntry).where(LeaderboardEntry.week_start == week_start))
    users = (await session.execute(select(User).order_by(desc(User.weekly_xp)).limit(200))).scalars().all()
    for rank, user in enumerate(users, start=1):
        session.add(
            LeaderboardEntry(
                user_id=user.id,
                username=user.username,
                avatar_color=user.avatar_color,
                weekly_xp=user.weekly_xp,
                week_start=week_start,
                rank=rank,
            )
        )
    await session.commit()


@router.get("/weekly")
async def weekly_leaderboard(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    week_start = _week_start(datetime.utcnow())
    entries = (
        await session.execute(select(LeaderboardEntry).where(LeaderboardEntry.week_start == week_start).order_by(LeaderboardEntry.rank))
    ).scalars().all()
    if len(entries) == 0:
        await _refresh_week_entries(session, week_start)
        entries = (
            await session.execute(select(LeaderboardEntry).where(LeaderboardEntry.week_start == week_start).order_by(LeaderboardEntry.rank))
        ).scalars().all()
    return {"items": [_serialize_entry(item) for item in entries], "week_start": week_start}


@router.get("/friends")
async def friends_leaderboard(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    connections = (
        await session.execute(
            select(FriendConnection).where(
                ((FriendConnection.requester_id == user.id) | (FriendConnection.receiver_id == user.id))
                & (FriendConnection.status == "accepted")
            )
        )
    ).scalars().all()

    ids = {user.id}
    for conn in connections:
        ids.add(conn.receiver_id if conn.requester_id == user.id else conn.requester_id)

    friends = (await session.execute(select(User).where(User.id.in_(list(ids))).order_by(desc(User.weekly_xp)))).scalars().all()
    items = [
        {
            "user_id": friend.id,
            "username": friend.username,
            "weekly_xp": friend.weekly_xp,
            "avatar_color": friend.avatar_color,
        }
        for friend in friends
    ]
    return {"items": items}
