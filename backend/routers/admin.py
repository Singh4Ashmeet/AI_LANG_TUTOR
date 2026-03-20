from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from ..config import settings
from ..database import get_session
from ..dependencies import require_admin
from ..models.active_session import ActiveSession
from ..models.admin import AdminLog
from ..models.extra import Achievement, Curriculum, LeaderboardEntry, Notification, UserAchievement, WordOfDay
from ..models.otp import OTPCode
from ..models.session import Session
from ..models.user import User
from ..models.vocabulary import VocabularyItem
from ..services.agents import call_feedback_coach, call_lesson_architect
from ..services.crypto import decrypt_value, encrypt_value
from ..services.email import EmailDeliveryError, send_otp_email
from ..services.otp import generate_otp_code

router = APIRouter(prefix="/admin", tags=["admin"])


class TotpConfirmRequest(BaseModel):
    code: str


def _serialize_user(user: User) -> dict:
    data = user.model_dump()
    data.pop("hashed_password", None)
    data.pop("totp_secret", None)
    data.pop("totp_pending_secret", None)
    data["_id"] = data.get("id")
    return data


def _serialize_session(item: Session) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


def _serialize_log(item: AdminLog) -> dict:
    data = item.model_dump()
    data["metadata"] = data.get("metadata_json", {})
    data["_id"] = data.get("id")
    return data


def _serialize_curriculum(item: Curriculum) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


def _serialize_leaderboard(item: LeaderboardEntry) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


def _serialize_word(item: WordOfDay) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    return data


def _serialize_active_session(item: ActiveSession, username: str | None = None) -> dict:
    data = item.model_dump()
    data["_id"] = data.get("id")
    if username:
        data["username"] = username
    return data


async def log_admin(
    session: AsyncSession,
    event_type: str,
    message: str,
    admin_id: Optional[int],
    user_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> None:
    session.add(
        AdminLog(
            event_type=event_type,
            message=message,
            metadata_json=metadata or {},
            admin_id=admin_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
        )
    )
    await session.commit()


@router.get("/stats")
async def stats(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.utcnow()
    today = now.date()
    week_start = today - timedelta(days=7)
    today_start = datetime.combine(today, datetime.min.time())
    week_start_dt = datetime.combine(week_start, datetime.min.time())

    total_users = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    active_today = (
        await session.execute(
            select(func.count()).select_from(User).where(User.last_session_date >= today_start)
        )
    ).scalar() or 0
    active_week = (
        await session.execute(
            select(func.count()).select_from(User).where(User.last_session_date >= week_start_dt)
        )
    ).scalar() or 0
    new_registrations = (
        await session.execute(select(func.count()).select_from(User).where(User.created_at >= week_start_dt))
    ).scalar() or 0
    total_sessions = (await session.execute(select(func.count()).select_from(Session))).scalar() or 0
    sessions_today = (
        await session.execute(select(func.count()).select_from(Session).where(Session.started_at >= today_start))
    ).scalar() or 0
    total_vocab_words = (await session.execute(select(func.count()).select_from(VocabularyItem))).scalar() or 0
    avg_streak = (await session.execute(select(func.coalesce(func.avg(User.streak), 0)))).scalar() or 0

    daily_active: list[dict[str, Any]] = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_dt = datetime.combine(day, datetime.min.time())
        next_day_dt = day_dt + timedelta(days=1)
        count = (
            await session.execute(
                select(func.count()).select_from(User).where(
                    User.last_session_date >= day_dt,
                    User.last_session_date < next_day_dt,
                )
            )
        ).scalar() or 0
        daily_active.append({"date": day.isoformat(), "count": count})

    type_results = (
        await session.execute(
            select(Session.session_type, func.count()).group_by(Session.session_type).order_by(func.count().desc())
        )
    ).all()
    session_types = [{"type": row[0] or "unknown", "count": row[1]} for row in type_results]

    lang_results = (
        await session.execute(
            select(User.target_language, func.count())
            .group_by(User.target_language)
            .order_by(func.count().desc())
            .limit(8)
        )
    ).all()
    top_languages = [{"lang": row[0] or "unknown", "count": row[1]} for row in lang_results]

    return {
        "total_users": total_users,
        "active_today": active_today,
        "active_week": active_week,
        "new_registrations": new_registrations,
        "total_sessions": total_sessions,
        "sessions_today": sessions_today,
        "total_vocab_words": total_vocab_words,
        "avg_streak": float(avg_streak),
        "daily_active": daily_active,
        "session_types": session_types,
        "top_languages": top_languages,
    }


@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    q: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 25,
):
    query = select(User)
    if q:
        query = query.where(or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if status_filter == "active":
        query = query.where(User.is_active == True)
    if status_filter == "suspended":
        query = query.where(User.is_active == False)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    items = (await session.execute(query.offset(skip).limit(limit))).scalars().all()
    return {"items": [_serialize_user(item) for item in items], "total": total}


@router.get("/users/{user_id}")
async def user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    payload = _serialize_user(user)
    payload["sessions_count"] = (
        await session.execute(select(func.count()).select_from(Session).where(Session.user_id == user.id))
    ).scalar() or 0
    payload["vocab_count"] = (
        await session.execute(select(func.count()).select_from(VocabularyItem).where(VocabularyItem.user_id == user.id))
    ).scalar() or 0
    return payload


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    updates: dict,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    allowed = {
        "username",
        "native_language",
        "target_language",
        "cefr_level",
        "daily_goal_minutes",
        "tutor_persona",
        "tutor_name",
        "theme",
        "sounds_enabled",
        "notification_time",
        "is_active",
    }
    applied: dict[str, Any] = {}
    for key, value in updates.items():
        if key in allowed and hasattr(user, key):
            setattr(user, key, value)
            applied[key] = value

    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await log_admin(session, "admin_action", "Updated user profile", admin.id, user_id, {"updates": applied})
    return _serialize_user(user)


@router.put("/users/{user_id}/role")
async def update_role(
    user_id: int,
    payload: dict,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    role = payload.get("role")
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = role
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await log_admin(session, "admin_action", f"Role changed to {role}", admin.id, user_id)
    return {"success": True}


@router.put("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    payload: dict,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    is_active = bool(payload.get("is_active", False))
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await log_admin(session, "admin_action", "User status updated", admin.id, user_id, {"is_active": is_active})
    return {"success": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(User).where(User.id == user_id))
    await session.execute(delete(Session).where(Session.user_id == user_id))
    await session.execute(delete(VocabularyItem).where(VocabularyItem.user_id == user_id))
    await session.execute(delete(ActiveSession).where(ActiveSession.user_id == user_id))
    await session.execute(delete(UserAchievement).where(UserAchievement.user_id == user_id))
    await session.execute(delete(Notification).where(Notification.user_id == user_id))
    await session.commit()
    await log_admin(session, "user_deleted", "User deleted", admin.id, user_id)
    return {"success": True}


@router.delete("/users/{user_id}/session")
async def force_logout(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(ActiveSession).where(ActiveSession.user_id == user_id, ActiveSession.is_valid == True).values(is_valid=False)
    )
    await session.commit()
    await log_admin(session, "admin_action", "Forced user logout", admin.id, user_id)
    return {"success": True}


@router.post("/users/{user_id}/reset-otp")
async def reset_otp(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await session.execute(delete(OTPCode).where(OTPCode.email == user.email))
    await session.commit()
    await log_admin(session, "admin_action", "Reset OTP codes", admin.id, user_id)
    return {"success": True}


@router.get("/sessions")
async def list_sessions(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 25,
):
    items = (await session.execute(select(Session).order_by(Session.started_at.desc()).offset(skip).limit(limit))).scalars().all()
    total = (await session.execute(select(func.count()).select_from(Session))).scalar() or 0
    return {"items": [_serialize_session(item) for item in items], "total": total}


@router.get("/sessions/{session_id}")
async def session_detail(
    session_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    item = (await session.execute(select(Session).where(Session.id == session_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _serialize_session(item)


@router.get("/logs")
async def logs(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 50,
    event_type: str | None = None,
):
    query = select(AdminLog).order_by(AdminLog.created_at.desc())
    if event_type:
        query = query.where(AdminLog.event_type.ilike(f"%{event_type}%"))

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    items = (await session.execute(query.offset(skip).limit(limit))).scalars().all()
    return {"items": [_serialize_log(item) for item in items], "total": total}


@router.get("/logs/export")
async def export_logs(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    event_type: str | None = None,
):
    query = select(AdminLog).order_by(AdminLog.created_at.desc())
    if event_type:
        query = query.where(AdminLog.event_type.ilike(f"%{event_type}%"))
    items = (await session.execute(query)).scalars().all()
    return {"items": [_serialize_log(item) for item in items]}


@router.delete("/logs/old")
async def clear_old_logs(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    cutoff = datetime.utcnow() - timedelta(days=90)
    await session.execute(delete(AdminLog).where(AdminLog.created_at < cutoff))
    await session.commit()
    await log_admin(session, "admin_action", "Cleared logs older than 90 days", admin.id)
    return {"success": True}


@router.get("/curriculum")
async def list_curriculum(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    items = (await session.execute(select(Curriculum))).scalars().all()
    return {"items": [_serialize_curriculum(item) for item in items]}


@router.post("/curriculum/regenerate/{lang_pair}")
async def regenerate_curriculum(
    lang_pair: str,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    prompt = {
        "role": "user",
        "content": (
            "Generate curriculum JSON with 5 sections and 8-12 skills per section. "
            "Return JSON shape: {sections:[{section_index,title,description,color,emoji,skills:[{skill_id,title,emoji,description,difficulty,tip_cards:[{title,explanation,examples:[{target,native}]}]}]}]}."
        ),
    }
    result = await call_lesson_architect([prompt], {"id": admin.id, "language_pair": lang_pair})
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Curriculum generation failed")

    sections = result.get("sections", [])
    existing = (await session.execute(select(Curriculum).where(Curriculum.language_pair == lang_pair))).scalar_one_or_none()
    now = datetime.utcnow()
    if existing:
        existing.sections = sections
        existing.updated_at = now
        session.add(existing)
    else:
        session.add(Curriculum(language_pair=lang_pair, sections=sections, generated_at=now, updated_at=now))
    await session.commit()
    await log_admin(session, "admin_action", "Regenerated curriculum", admin.id, metadata={"lang_pair": lang_pair})
    return {"success": True}


@router.put("/curriculum/{curriculum_id}/skill/{skill_id}")
async def update_skill(
    curriculum_id: int,
    skill_id: str,
    payload: dict,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    curriculum = (await session.execute(select(Curriculum).where(Curriculum.id == curriculum_id))).scalar_one_or_none()
    if not curriculum:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found")

    updated = False
    sections = list(curriculum.sections or [])
    for section in sections:
        for skill in section.get("skills", []):
            if str(skill.get("skill_id")) == str(skill_id):
                skill.update(payload)
                updated = True
                break
        if updated:
            break

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    curriculum.sections = sections
    curriculum.updated_at = datetime.utcnow()
    session.add(curriculum)
    await session.commit()
    return {"success": True}


@router.get("/leaderboard")
async def admin_leaderboard(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    items = (await session.execute(select(LeaderboardEntry).order_by(LeaderboardEntry.week_start.desc()).limit(300))).scalars().all()
    return {"items": [_serialize_leaderboard(item) for item in items]}


@router.delete("/leaderboard/{user_id}")
async def remove_from_leaderboard(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(delete(LeaderboardEntry).where(LeaderboardEntry.user_id == user_id))
    await session.commit()
    await log_admin(session, "admin_action", "Removed user from leaderboard", admin.id, user_id)
    return {"success": True}


@router.get("/system/status")
async def system_status(admin: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    def flag(value: Any) -> bool:
        return bool(value)

    collections = {
        "users": (await session.execute(select(func.count()).select_from(User))).scalar() or 0,
        "sessions": (await session.execute(select(func.count()).select_from(Session))).scalar() or 0,
        "vocabulary": (await session.execute(select(func.count()).select_from(VocabularyItem))).scalar() or 0,
        "curriculum": (await session.execute(select(func.count()).select_from(Curriculum))).scalar() or 0,
        "logs": (await session.execute(select(func.count()).select_from(AdminLog))).scalar() or 0,
    }

    return {
        "env": {
            "DATABASE_URL": flag(settings.DATABASE_URL),
            "SECRET_KEY": flag(settings.SECRET_KEY),
            "GROQ_API_KEY": flag(settings.GROQ_API_KEY),
            "GEMINI_API_KEY": flag(settings.GEMINI_API_KEY),
            "GMAIL_ADDRESS": flag(settings.GMAIL_ADDRESS),
            "GMAIL_APP_PASSWORD": flag(settings.GMAIL_APP_PASSWORD),
            "WHISPER_MODEL": flag(settings.WHISPER_MODEL),
        },
        "collections": collections,
    }


@router.post("/system/test-llm")
async def test_llm(admin: User = Depends(require_admin)):
    response = await call_feedback_coach([{"role": "user", "content": "Say OK in one word."}], admin.model_dump())
    return {"response": response}


@router.post("/system/test-otp")
async def test_otp(admin: User = Depends(require_admin)):
    code = generate_otp_code()
    try:
        await send_otp_email(admin.email, admin.username or "Admin", code)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OTP email test failed: {exc.reason}",
        ) from exc
    return {"success": True}


@router.get("/system/sessions")
async def active_sessions(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(ActiveSession, User.username)
            .join(User, User.id == ActiveSession.user_id)
            .where(ActiveSession.is_valid == True)
            .order_by(ActiveSession.last_active.desc())
        )
    ).all()

    items = [_serialize_active_session(active, username) for active, username in rows]
    return {"items": items}


@router.delete("/system/sessions/all")
async def kill_all_sessions(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(update(ActiveSession).values(is_valid=False))
    await session.commit()
    await log_admin(session, "admin_action", "Killed all sessions", admin.id)
    return {"success": True}


@router.get("/system/totp/setup")
async def totp_setup(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if admin.totp_secret:
        return {"enabled": True}

    secret = pyotp.random_base32()
    otpauth = pyotp.TOTP(secret).provisioning_uri(name=admin.email, issuer_name="LinguAI")
    admin.totp_pending_secret = encrypt_value(secret)
    admin.updated_at = datetime.utcnow()
    session.add(admin)
    await session.commit()
    return {"enabled": False, "otpauth_url": otpauth, "secret": secret}


@router.post("/system/totp/confirm")
async def totp_confirm(
    payload: TotpConfirmRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    pending = admin.totp_pending_secret
    if not pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending TOTP setup.")

    secret = decrypt_value(pending)
    if not pyotp.TOTP(secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")

    admin.totp_secret = encrypt_value(secret)
    admin.totp_pending_secret = None
    admin.updated_at = datetime.utcnow()
    session.add(admin)
    await session.commit()
    await log_admin(session, "admin_action", "Enabled TOTP", admin.id)
    return {"enabled": True}


@router.get("/word-of-day")
async def admin_word_of_day(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    items = (await session.execute(select(WordOfDay).order_by(WordOfDay.date.desc()).limit(30))).scalars().all()
    return {"items": [_serialize_word(item) for item in items]}


@router.post("/word-of-day/seed")
async def seed_word_of_day(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    today = datetime.utcnow().date()
    today_dt = datetime.combine(today, datetime.min.time())

    pairs = (await session.execute(select(Curriculum.language_pair))).scalars().all()
    for pair in pairs:
        exists = (
            await session.execute(
                select(WordOfDay).where(WordOfDay.date == today_dt, WordOfDay.language_pair == pair)
            )
        ).scalar_one_or_none()
        if exists:
            continue

        prompt = {
            "role": "user",
            "content": (
                "Generate JSON: {word, translation, part_of_speech, example_sentence, example_translation}. "
                f"Language pair: {pair}."
            ),
        }
        result = await call_lesson_architect([prompt], admin.model_dump())
        if not isinstance(result, dict):
            continue

        session.add(
            WordOfDay(
                date=today_dt,
                language_pair=pair,
                word=result.get("word", ""),
                translation=result.get("translation", ""),
                part_of_speech=result.get("part_of_speech"),
                example_sentence=result.get("example_sentence"),
                example_translation=result.get("example_translation"),
                audio_cached=False,
            )
        )

    await session.commit()
    await log_admin(session, "admin_action", "Seeded word of day", admin.id)
    return {"success": True}
