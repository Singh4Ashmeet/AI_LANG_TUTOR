from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, func, or_, select

from ..auth import hash_password, verify_password
from ..config import settings
from ..database import get_session
from ..dependencies import get_current_user
from ..models.extra import Challenge, FriendConnection, GrammarStat
from ..models.otp import OTPCode
from ..models.session import Session
from ..models.user import User
from ..models.vocabulary import VocabularyItem
from ..services.email import send_otp_email
from ..services.otp import generate_otp_code, hash_otp_code, verify_otp_code
from ..services.sessions import invalidate_session

router = APIRouter(prefix="/users", tags=["users"])
history_router = APIRouter(prefix="/history", tags=["history"])
onboarding_router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class UpdateProfileRequest(BaseModel):
    tutor_persona: str | None = None
    tutor_name: str | None = None
    daily_goal_minutes: int | None = None
    theme: str | None = None
    sounds_enabled: bool | None = None
    immersion_mode: bool | None = None
    notification_time: str | None = None
    native_language: str | None = None
    target_language: str | None = None
    goals: list[str] | None = None


class UpdatePasswordRequest(BaseModel):
    new_password: str
    otp_code: str
    current_password: str | None = None


class DeleteAccountRequest(BaseModel):
    confirm: str
    otp_code: str


class OnboardingRequest(BaseModel):
    native_language: str
    target_language: str
    goals: list[str]
    tutor_persona: str
    daily_goal_minutes: int


class ChallengeCreateRequest(BaseModel):
    challenged_id: int
    challenge_type: str
    target_value: int = 500


def serialize_user(user: User) -> dict:
    data = user.model_dump()
    data.pop("hashed_password", None)
    data.pop("totp_secret", None)
    data.pop("totp_pending_secret", None)
    data["_id"] = data.get("id")
    return data


def serialize_session(item: Session) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


def serialize_challenge(item: Challenge) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


def serialize_friend_connection(item: FriendConnection) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


async def _latest_otp(session: AsyncSession, email: str, purpose: str) -> OTPCode | None:
    stmt = (
        select(OTPCode)
        .where(OTPCode.email == email, OTPCode.purpose == purpose, OTPCode.used == False)
        .order_by(desc(OTPCode.created_at))
    )
    return (await session.execute(stmt)).scalars().first()


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return serialize_user(user)


@router.put("/me")
async def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return serialize_user(user)


@router.get("/me/stats")
async def get_stats(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    vocab_counts = {}
    for status_name in ("new", "learning", "known", "mastered"):
        stmt = select(func.count()).select_from(VocabularyItem).where(
            VocabularyItem.user_id == user.id, VocabularyItem.status == status_name
        )
        vocab_counts[status_name] = (await session.execute(stmt)).scalar() or 0

    total_sessions = (
        await session.execute(select(func.count()).select_from(Session).where(Session.user_id == user.id))
    ).scalar() or 0

    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    end = start + timedelta(days=1)
    minutes_today_stmt = select(func.coalesce(func.sum(Session.duration_seconds), 0)).where(
        Session.user_id == user.id, Session.started_at >= start, Session.started_at < end
    )
    minutes_today = int(((await session.execute(minutes_today_stmt)).scalar() or 0) / 60)

    weak_grammar_stmt = (
        select(GrammarStat)
        .where(GrammarStat.user_id == user.id)
        .order_by(GrammarStat.errors.desc(), GrammarStat.last_error_at.desc())
        .limit(3)
    )
    weak_grammar_items = (await session.execute(weak_grammar_stmt)).scalars().all()

    recent_sessions_stmt = (
        select(Session)
        .where(Session.user_id == user.id, Session.session_type == "lesson")
        .order_by(desc(Session.started_at))
        .limit(6)
    )
    recent_sessions = (await session.execute(recent_sessions_stmt)).scalars().all()
    recent_mistakes = []
    for lesson_session in recent_sessions:
        for exercise in lesson_session.exercises or []:
            if exercise.get("is_correct") is False and exercise.get("content"):
                recent_mistakes.append(
                    {
                        "prompt": str(exercise.get("content")),
                        "rule": exercise.get("grammar_rule"),
                        "answer_mode": exercise.get("answer_mode"),
                    }
                )
    vocab_due_stmt = select(func.count()).select_from(VocabularyItem).where(
        VocabularyItem.user_id == user.id, VocabularyItem.next_review <= datetime.utcnow()
    )
    vocabulary_due = (await session.execute(vocab_due_stmt)).scalar() or 0

    return {
        "xp": user.xp,
        "weekly_xp": user.weekly_xp,
        "total_xp": user.total_xp,
        "streak": user.streak,
        "streak_freeze": user.streak_freeze,
        "gems": user.gems,
        "hearts": user.hearts,
        "minutes_today": minutes_today,
        "total_minutes_practiced": user.total_minutes_practiced,
        "total_lessons_complete": user.total_lessons_complete,
        "total_words_learned": user.total_words_learned,
        "achievements_earned": len(user.achievements_earned or []),
        "daily_goal_minutes": user.daily_goal_minutes,
        "vocabulary": vocab_counts,
        "vocabulary_due": vocabulary_due,
        "total_sessions": total_sessions,
        "weak_grammar": [
            {"rule": item.rule, "errors": item.errors, "mastery": item.mastery}
            for item in weak_grammar_items
        ],
        "recent_mistakes": recent_mistakes[:3],
    }


@router.put("/me/password")
async def update_password(
    payload: UpdatePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if payload.current_password and not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password")

    otp_doc = await _latest_otp(session, user.email, "reset_password")
    if not otp_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")

    otp_doc.attempts += 1
    if otp_doc.attempts > settings.MAX_OTP_ATTEMPTS:
        await session.execute(delete(OTPCode).where(OTPCode.id == otp_doc.id))
        await session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    if not verify_otp_code(payload.otp_code, otp_doc.code_hash):
        session.add(otp_doc)
        await session.commit()
        remaining = max(settings.MAX_OTP_ATTEMPTS - otp_doc.attempts, 0)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {remaining} attempts remaining.")

    otp_doc.used = True
    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = datetime.utcnow()
    session.add(otp_doc)
    session.add(user)
    await session.commit()
    await invalidate_session(session, user.id)
    return {"success": True}


@router.post("/me/delete/request-otp")
async def request_delete_otp(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(OTPCode).where(OTPCode.email == user.email, OTPCode.purpose == "delete_account"))
    code = generate_otp_code()
    now = datetime.utcnow()
    session.add(
        OTPCode(
            email=user.email,
            code_hash=hash_otp_code(code),
            purpose="delete_account",
            attempts=0,
            used=False,
            created_at=now,
            expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
    )
    await session.commit()
    background_tasks.add_task(send_otp_email, user.email, user.username, code)
    return {"message": "OTP sent to your email"}


@router.delete("/me")
async def delete_account(
    payload: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if payload.confirm.strip().upper() != "DELETE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type DELETE to confirm.")

    otp_doc = await _latest_otp(session, user.email, "delete_account")
    if not otp_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")

    otp_doc.attempts += 1
    if otp_doc.attempts > settings.MAX_OTP_ATTEMPTS:
        await session.execute(delete(OTPCode).where(OTPCode.id == otp_doc.id))
        await session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    if not verify_otp_code(payload.otp_code, otp_doc.code_hash):
        session.add(otp_doc)
        await session.commit()
        remaining = max(settings.MAX_OTP_ATTEMPTS - otp_doc.attempts, 0)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {remaining} attempts remaining.")

    await session.execute(delete(Session).where(Session.user_id == user.id))
    await session.execute(delete(VocabularyItem).where(VocabularyItem.user_id == user.id))
    await session.execute(
        delete(FriendConnection).where(
            or_(FriendConnection.requester_id == user.id, FriendConnection.receiver_id == user.id)
        )
    )
    await session.execute(delete(Challenge).where(or_(Challenge.challenger_id == user.id, Challenge.challenged_id == user.id)))
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
    await invalidate_session(session, user.id)
    return {"success": True}


@router.post("/me/refill-hearts")
async def refill_hearts(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if user.gems < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough gems")
    if user.hearts >= settings.MAX_HEARTS:
        return {"hearts": user.hearts, "gems": user.gems}
    user.gems -= 5
    user.hearts = min(settings.MAX_HEARTS, user.hearts + 1)
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    return {"hearts": user.hearts, "gems": user.gems}


@router.post("/me/buy-freeze")
async def buy_streak_freeze(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if user.gems < 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough gems")
    if user.streak_freeze >= 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum freezes reached")
    user.gems -= 20
    user.streak_freeze += 1
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    return {"streak_freeze": user.streak_freeze, "gems": user.gems}


@router.get("/search")
async def search_users(q: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = (
        select(User)
        .where(or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")), User.id != user.id)
        .limit(20)
    )
    items = (await session.execute(stmt)).scalars().all()
    return {"items": [serialize_user(item) for item in items]}


@router.post("/friends/request/{friend_id}")
async def request_friend(friend_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if friend_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot friend yourself")
    existing = (
        await session.execute(
            select(FriendConnection).where(
                or_(
                    (FriendConnection.requester_id == user.id) & (FriendConnection.receiver_id == friend_id),
                    (FriendConnection.requester_id == friend_id) & (FriendConnection.receiver_id == user.id),
                )
            )
        )
    ).scalars().first()
    if existing:
        existing.status = "pending"
        existing.requester_id = user.id
        existing.receiver_id = friend_id
        session.add(existing)
    else:
        session.add(FriendConnection(requester_id=user.id, receiver_id=friend_id, status="pending"))
    await session.commit()
    return {"success": True}


@router.post("/friends/accept/{friend_id}")
async def accept_friend(friend_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(FriendConnection).where(
        FriendConnection.requester_id == friend_id,
        FriendConnection.receiver_id == user.id,
        FriendConnection.status == "pending",
    )
    connection = (await session.execute(stmt)).scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found")
    connection.status = "accepted"
    session.add(connection)
    await session.commit()
    return {"success": True}


@router.delete("/friends/{friend_id}")
async def remove_friend(friend_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(
        delete(FriendConnection).where(
            or_(
                (FriendConnection.requester_id == user.id) & (FriendConnection.receiver_id == friend_id),
                (FriendConnection.requester_id == friend_id) & (FriendConnection.receiver_id == user.id),
            )
        )
    )
    await session.commit()
    return {"success": True}


@router.get("/friends")
async def list_friends(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    accepted_stmt = select(FriendConnection).where(
        or_(FriendConnection.requester_id == user.id, FriendConnection.receiver_id == user.id),
        FriendConnection.status == "accepted",
    )
    accepted = (await session.execute(accepted_stmt)).scalars().all()
    friend_ids = [item.receiver_id if item.requester_id == user.id else item.requester_id for item in accepted]
    if not friend_ids:
        friends = []
    else:
        users_stmt = select(User).where(User.id.in_(friend_ids))
        friends = (await session.execute(users_stmt)).scalars().all()

    incoming_requests = (
        await session.execute(
            select(FriendConnection).where(
                FriendConnection.receiver_id == user.id,
                FriendConnection.status == "pending",
            )
        )
    ).scalars().all()

    outgoing_requests = (
        await session.execute(
            select(FriendConnection).where(
                FriendConnection.requester_id == user.id,
                FriendConnection.status == "pending",
            )
        )
    ).scalars().all()

    incoming_ids = [item.requester_id for item in incoming_requests]
    outgoing_ids = [item.receiver_id for item in outgoing_requests]

    incoming_users = []
    outgoing_users = []
    if incoming_ids:
        incoming_users = (
            await session.execute(select(User).where(User.id.in_(incoming_ids)))
        ).scalars().all()
    if outgoing_ids:
        outgoing_users = (
            await session.execute(select(User).where(User.id.in_(outgoing_ids)))
        ).scalars().all()

    incoming_map = {item.id: item for item in incoming_users}
    outgoing_map = {item.id: item for item in outgoing_users}

    return {
        "items": [serialize_user(item) for item in friends],
        "incoming": [
            {
                **serialize_friend_connection(request),
                "user": serialize_user(incoming_map[request.requester_id]),
            }
            for request in incoming_requests
            if request.requester_id in incoming_map
        ],
        "outgoing": [
            {
                **serialize_friend_connection(request),
                "user": serialize_user(outgoing_map[request.receiver_id]),
            }
            for request in outgoing_requests
            if request.receiver_id in outgoing_map
        ],
    }


@router.post("/challenges/create")
async def create_challenge(
    payload: ChallengeCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    active_count_stmt = select(func.count()).select_from(Challenge).where(
        Challenge.challenger_id == user.id, Challenge.status == "active"
    )
    active_count = (await session.execute(active_count_stmt)).scalar() or 0
    if active_count >= 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Max 3 active challenges")

    now = datetime.utcnow()
    challenge = Challenge(
        challenger_id=user.id,
        challenged_id=payload.challenged_id,
        challenge_type=payload.challenge_type,
        target_value=payload.target_value,
        start_date=now,
        end_date=now + timedelta(days=7),
        status="active",
    )
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return {"id": challenge.id, "_id": challenge.id}


@router.get("/challenges")
async def list_challenges(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = (
        select(Challenge)
        .where(or_(Challenge.challenger_id == user.id, Challenge.challenged_id == user.id))
        .order_by(desc(Challenge.start_date))
    )
    items = (await session.execute(stmt)).scalars().all()
    return {"items": [serialize_challenge(item) for item in items]}


@router.put("/challenges/{challenge_id}/accept")
async def accept_challenge(challenge_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(Challenge).where(Challenge.id == challenge_id, Challenge.challenged_id == user.id)
    item = (await session.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found")
    item.status = "active"
    item.start_date = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"success": True}


@onboarding_router.post("/complete")
async def complete_onboarding(
    payload: OnboardingRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user.native_language = payload.native_language
    user.target_language = payload.target_language
    user.goals = payload.goals
    user.tutor_persona = payload.tutor_persona
    user.daily_goal_minutes = payload.daily_goal_minutes
    user.onboarding_complete = True
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    return {"success": True}


@history_router.get("")
async def list_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 20,
):
    stmt = (
        select(Session)
        .where(Session.user_id == user.id)
        .order_by(desc(Session.started_at))
        .offset(skip)
        .limit(limit)
    )
    items = (await session.execute(stmt)).scalars().all()
    total = (await session.execute(select(func.count()).select_from(Session).where(Session.user_id == user.id))).scalar() or 0
    return {"items": [serialize_session(item) for item in items], "total": total}


@history_router.get("/{session_id}")
async def session_detail(session_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    stmt = select(Session).where(Session.id == session_id, Session.user_id == user.id)
    item = (await session.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return serialize_session(item)
