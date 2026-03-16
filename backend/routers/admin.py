from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
import pyotp

from ..database import (
    active_sessions_collection,
    admin_logs_collection,
    otp_codes_collection,
    curriculum_collection,
    leaderboard_entries_collection,
    word_of_day_collection,
    sessions_collection,
    users_collection,
    vocabulary_collection,
)
from ..dependencies import require_admin
from ..config import settings
from ..services.crypto import decrypt_value, encrypt_value
from ..services.agents import call_lesson_architect, call_feedback_coach
from ..services.email import send_otp_email
from ..services.otp import generate_otp_code

router = APIRouter(prefix="/admin", tags=["admin"])


class TotpConfirmRequest(BaseModel):
    code: str


async def log_admin(event_type: str, message: str, admin_id: ObjectId | None, user_id: ObjectId | None = None, metadata: dict | None = None):
    await admin_logs_collection().insert_one(
        {
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
            "admin_id": admin_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
        }
    )


@router.get("/stats")
async def stats(admin=Depends(require_admin)):
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)
    
    users = users_collection()
    sessions = sessions_collection()
    
    total_users = await users.count_documents({})
    active_today = await users.count_documents({"last_session_date": {"$gte": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)}})
    active_week = await users.count_documents({"last_session_date": {"$gte": datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)}})
    new_registrations = await users.count_documents({"created_at": {"$gte": datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)}})
    total_sessions = await sessions.count_documents({})
    sessions_today = await sessions.count_documents({"started_at": {"$gte": datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)}})
    
    # Daily Active Users (Last 30 days)
    daily_active = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_dt = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        next_day_dt = day_dt + timedelta(days=1)
        count = await users.count_documents({"last_session_date": {"$gte": day_dt, "$lt": next_day_dt}})
        daily_active.append({"date": day.isoformat(), "count": count})
        
    # Sessions by Type
    pipeline = [
        {"$group": {"_id": "$session_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    type_cursor = sessions.aggregate(pipeline)
    session_types = [{"type": i["_id"] or "unknown", "count": i["count"]} async for i in type_cursor]

    # Top Languages
    lang_pipeline = [
        {"$group": {"_id": "$target_language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 6}
    ]
    lang_cursor = users.aggregate(lang_pipeline)
    top_languages = [{"lang": i["_id"] or "Unknown", "count": i["count"]} async for i in lang_cursor]

    return {
        "total_users": total_users,
        "active_today": active_today,
        "active_week": active_week,
        "new_registrations": new_registrations,
        "total_sessions": total_sessions,
        "sessions_today": sessions_today,
        "daily_active": daily_active,
        "session_types": session_types,
        "top_languages": top_languages,
    }


@router.get("/users")
async def list_users(
    admin=Depends(require_admin),
    q: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 25,
):
    query: dict = {}
    if q:
        query["$or"] = [{"username": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    if status_filter == "active":
        query["is_active"] = True
    if status_filter == "suspended":
        query["is_active"] = False

    cursor = users_collection().find(query).skip(skip).limit(limit)
    items = []
    async for user in cursor:
        user.pop("password_hash", None)
        user.pop("totp_secret", None)
        user.pop("totp_pending_secret", None)
        user["_id"] = str(user["_id"])
        items.append(user)
    total = await users_collection().count_documents(query)
    return {"items": items, "total": total}


@router.get("/users/{user_id}")
async def user_detail(user_id: str, admin=Depends(require_admin)):
    user = await users_collection().find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.pop("password_hash", None)
    user.pop("totp_secret", None)
    user.pop("totp_pending_secret", None)
    user["_id"] = str(user["_id"])
    return user


@router.put("/users/{user_id}")
async def update_user(user_id: str, updates: dict, admin=Depends(require_admin)):
    await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    await log_admin("admin_action", "Updated user profile", admin["_id"], ObjectId(user_id), {"updates": updates})
    return {"success": True}


@router.put("/users/{user_id}/role")
async def update_role(user_id: str, payload: dict, admin=Depends(require_admin)):
    role = payload.get("role")
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": {"role": role}})
    await log_admin("admin_action", f"Role changed to {role}", admin["_id"], ObjectId(user_id))
    return {"success": True}


@router.put("/users/{user_id}/suspend")
async def suspend_user(user_id: str, payload: dict, admin=Depends(require_admin)):
    is_active = payload.get("is_active", False)
    await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": {"is_active": is_active}})
    event = "user_banned" if not is_active else "admin_action"
    await log_admin(event, "User status updated", admin["_id"], ObjectId(user_id), {"is_active": is_active})
    return {"success": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin=Depends(require_admin)):
    await users_collection().delete_one({"_id": ObjectId(user_id)})
    await sessions_collection().delete_many({"user_id": ObjectId(user_id)})
    await vocabulary_collection().delete_many({"user_id": ObjectId(user_id)})
    await log_admin("user_deleted", "User deleted", admin["_id"], ObjectId(user_id))
    return {"success": True}


@router.delete("/users/{user_id}/session")
async def force_logout(user_id: str, admin=Depends(require_admin)):
    await active_sessions_collection().update_one(
        {"user_id": ObjectId(user_id), "is_valid": True},
        {"$set": {"is_valid": False}},
    )
    await log_admin("admin_action", "Forced user logout", admin["_id"], ObjectId(user_id))
    return {"success": True}


@router.post("/users/{user_id}/reset-otp")
async def reset_otp(user_id: str, admin=Depends(require_admin)):
    user = await users_collection().find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await otp_codes_collection().delete_many({"email": user.get("email")})
    await log_admin("admin_action", "Reset OTP codes", admin["_id"], ObjectId(user_id))
    return {"success": True}


@router.get("/system/totp/setup")
async def totp_setup(admin=Depends(require_admin)):
    if admin.get("totp_secret"):
        return {"enabled": True}
    secret = pyotp.random_base32()
    otpauth = pyotp.TOTP(secret).provisioning_uri(name=admin.get("email"), issuer_name="LinguAI")
    await users_collection().update_one(
        {"_id": admin["_id"]},
        {"$set": {"totp_pending_secret": encrypt_value(secret), "updated_at": datetime.now(timezone.utc)}},
    )
    return {"enabled": False, "otpauth_url": otpauth, "secret": secret}


@router.post("/system/totp/confirm")
async def totp_confirm(payload: TotpConfirmRequest, admin=Depends(require_admin)):
    pending = admin.get("totp_pending_secret")
    if not pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending TOTP setup.")
    secret = decrypt_value(pending)
    totp = pyotp.TOTP(secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")

    await users_collection().update_one(
        {"_id": admin["_id"]},
        {
            "$set": {"totp_secret": encrypt_value(secret), "updated_at": datetime.now(timezone.utc)},
            "$unset": {"totp_pending_secret": ""},
        },
    )
    await log_admin("admin_action", "Enabled TOTP", admin["_id"])
    return {"enabled": True}


@router.get("/sessions")
async def list_sessions(admin=Depends(require_admin), skip: int = 0, limit: int = 25):
    cursor = sessions_collection().find({}).skip(skip).limit(limit).sort("started_at", -1)
    items = []
    async for session in cursor:
        session["_id"] = str(session["_id"])
        session["user_id"] = str(session["user_id"])
        items.append(session)
    total = await sessions_collection().count_documents({})
    return {"items": items, "total": total}


@router.get("/sessions/{session_id}")
async def session_detail(session_id: str, admin=Depends(require_admin)):
    session = await sessions_collection().find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session["_id"] = str(session["_id"])
    session["user_id"] = str(session["user_id"])
    return session


@router.get("/logs")
async def logs(admin=Depends(require_admin), skip: int = 0, limit: int = 50, event_type: str | None = None):
    query = {"event_type": event_type} if event_type else {}
    cursor = admin_logs_collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for log in cursor:
        log["_id"] = str(log["_id"])
        if log.get("admin_id"):
            log["admin_id"] = str(log["admin_id"])
        if log.get("user_id"):
            log["user_id"] = str(log["user_id"])
        items.append(log)
    total = await admin_logs_collection().count_documents(query)
    return {"items": items, "total": total}


@router.get("/logs/export")
async def export_logs(admin=Depends(require_admin), event_type: str | None = None):
    query = {"event_type": event_type} if event_type else {}
    cursor = admin_logs_collection().find(query).sort("created_at", -1)
    items = []
    async for log in cursor:
        log["_id"] = str(log["_id"])
        if log.get("admin_id"):
            log["admin_id"] = str(log["admin_id"])
        if log.get("user_id"):
            log["user_id"] = str(log["user_id"])
        items.append(log)
    return {"items": items}


@router.get("/curriculum")
async def list_curriculum(admin=Depends(require_admin)):
    cursor = curriculum_collection().find({})
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        items.append(item)
    return {"items": items}


@router.post("/curriculum/regenerate/{lang_pair}")
async def regenerate_curriculum(lang_pair: str, admin=Depends(require_admin)):
    prompt = {
        "role": "user",
        "content": (
            "Generate a curriculum JSON for a language pair with 5 sections and 40-60 skills total. "
            "Each section must include 8-12 skills. Return JSON only."
        ),
    }
    result = await call_lesson_architect([prompt], admin)
    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Curriculum generation failed")
    result["language_pair"] = lang_pair
    result["generated_at"] = datetime.now(timezone.utc)
    await curriculum_collection().update_one({"language_pair": lang_pair}, {"$set": result}, upsert=True)
    return {"success": True}


@router.put("/curriculum/{curriculum_id}/skill/{skill_id}")
async def update_skill(curriculum_id: str, skill_id: int, payload: dict, admin=Depends(require_admin)):
    curriculum = await curriculum_collection().find_one({"_id": ObjectId(curriculum_id)})
    if not curriculum:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found")
    updated = False
    for section in curriculum.get("sections", []):
        for skill in section.get("skills", []):
            if int(skill.get("skill_id", -1)) == int(skill_id):
                skill.update(payload)
                updated = True
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    await curriculum_collection().update_one({"_id": ObjectId(curriculum_id)}, {"$set": {"sections": curriculum["sections"]}})
    return {"success": True}


@router.get("/leaderboard")
async def admin_leaderboard(admin=Depends(require_admin)):
    cursor = leaderboard_entries_collection().find({}).sort("week_start", -1).limit(200)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        items.append(item)
    return {"items": items}


@router.delete("/leaderboard/{user_id}")
async def remove_from_leaderboard(user_id: str, admin=Depends(require_admin)):
    await leaderboard_entries_collection().delete_many({"user_id": ObjectId(user_id)})
    await log_admin("admin_action", "Removed user from leaderboard", admin["_id"], ObjectId(user_id))
    return {"success": True}


@router.get("/system/status")
async def system_status(admin=Depends(require_admin)):
    def flag(value: str | None) -> bool:
        return bool(value)

    return {
        "env": {
            "MONGODB_URL": flag(settings.mongodb_url),
            "SECRET_KEY": flag(settings.secret_key),
            "GROQ_API_KEY": flag(settings.groq_api_key),
            "GEMINI_API_KEY": flag(settings.gemini_api_key),
            "GMAIL_ADDRESS": flag(settings.gmail_address),
            "GMAIL_APP_PASSWORD": flag(settings.gmail_app_password),
        }
    }


@router.post("/system/test-llm")
async def test_llm(admin=Depends(require_admin)):
    response = await call_feedback_coach([{"role": "user", "content": "Say OK."}], admin)
    return {"response": response}


@router.post("/system/test-otp")
async def test_otp(admin=Depends(require_admin)):
    code = generate_otp_code()
    await send_otp_email(admin.get("email"), admin.get("username", "Admin"), code)
    return {"success": True}


@router.get("/system/sessions")
async def active_sessions(admin=Depends(require_admin)):
    pipeline = [
        {"$match": {"is_valid": True}},
        {"$sort": {"last_active": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info",
            }
        },
        {"$unwind": "$user_info"},
    ]
    cursor = active_sessions_collection().aggregate(pipeline)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["user_id"] = str(item["user_id"])
        item["username"] = item["user_info"].get("username", "Unknown")
        item.pop("user_info", None)
        items.append(item)
    return {"items": items}


@router.delete("/system/sessions/all")
async def kill_all_sessions(admin=Depends(require_admin)):
    await active_sessions_collection().update_many({}, {"$set": {"is_valid": False}})
    await log_admin("admin_action", "Killed all sessions", admin["_id"])
    return {"success": True}


@router.get("/word-of-day")
async def admin_word_of_day(admin=Depends(require_admin)):
    cursor = word_of_day_collection().find({}).sort("date", -1).limit(20)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        items.append(item)
    return {"items": items}


@router.post("/word-of-day/seed")
async def seed_word_of_day(admin=Depends(require_admin)):
    today = datetime.now(timezone.utc).date()
    pairs = []
    cursor = curriculum_collection().find({})
    async for item in cursor:
        if item.get("language_pair"):
            pairs.append(item["language_pair"])
    for pair in pairs:
        existing = await word_of_day_collection().find_one({"date": today, "language_pair": pair})
        if existing:
            continue
        prompt = {
            "role": "user",
            "content": (
                "Generate a Word of the Day JSON: {word, translation, part_of_speech, example_sentence, example_translation}. "
                f"Language pair: {pair}."
            ),
        }
        result = await call_lesson_architect([prompt], admin)
        if isinstance(result, dict):
            await word_of_day_collection().insert_one(
                {
                    "date": today,
                    "language_pair": pair,
                    "word": result.get("word"),
                    "translation": result.get("translation"),
                    "part_of_speech": result.get("part_of_speech"),
                    "example_sentence": result.get("example_sentence"),
                    "example_translation": result.get("example_translation"),
                    "audio_cached": False,
                }
            )
    return {"success": True, "pairs": pairs}
