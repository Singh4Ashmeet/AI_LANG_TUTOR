from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import hash_password, verify_password
from ..config import settings
from ..database import (
    challenges_collection,
    friend_connections_collection,
    grammar_stats_collection,
    otp_codes_collection,
    sessions_collection,
    users_collection,
    vocabulary_collection,
)
from ..dependencies import get_current_user
from ..limiters import limiter
from ..services.email import send_otp_email
from ..services.otp import (
    allow_otp_request,
    generate_otp_code,
    hash_otp_code,
    otp_expired,
    record_otp_request,
    verify_otp_code,
)
from ..services.sessions import invalidate_session

router = APIRouter(prefix="/users", tags=["users"])
history_router = APIRouter(prefix="/history", tags=["history"])
onboarding_router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class UpdateProfileRequest(BaseModel):
    tutor_persona: str | None = None
    daily_goal_minutes: int | None = None
    theme: str | None = None
    sounds_enabled: bool | None = None
    immersion_mode: bool | None = None
    notification_time: str | None = None


class UpdatePasswordRequest(BaseModel):
    new_password: str
    otp_code: str
    current_password: str | None = None


class OnboardingRequest(BaseModel):
    native_language: str
    target_language: str
    goals: list[str]
    tutor_persona: str
    daily_goal_minutes: int


class DeleteAccountRequest(BaseModel):
    confirm: str
    otp_code: str


class ChallengeCreateRequest(BaseModel):
    challenged_id: str
    challenge_type: str
    target_value: int


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    user = {**user}
    user.pop("password_hash", None)
    user.pop("totp_secret", None)
    user.pop("totp_pending_secret", None)
    user["_id"] = str(user["_id"])
    return user


@router.put("/me")
async def update_me(payload: UpdateProfileRequest, user=Depends(get_current_user)):
    updates = {}
    if payload.tutor_persona is not None:
        updates["tutor_persona"] = payload.tutor_persona
    if payload.daily_goal_minutes is not None:
        updates["daily_goal_minutes"] = payload.daily_goal_minutes
    if payload.theme is not None:
        updates["theme"] = payload.theme
    if payload.sounds_enabled is not None:
        updates["sounds_enabled"] = payload.sounds_enabled
    if payload.immersion_mode is not None:
        updates["immersion_mode"] = payload.immersion_mode
    if payload.notification_time is not None:
        updates["notification_time"] = payload.notification_time

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await users_collection().update_one({"_id": user["_id"]}, {"$set": updates})

    updated = await users_collection().find_one({"_id": user["_id"]})
    updated.pop("password_hash", None)
    updated.pop("totp_secret", None)
    updated.pop("totp_pending_secret", None)
    updated["_id"] = str(updated["_id"])
    return updated


@router.put("/me/password")
async def update_password(payload: UpdatePasswordRequest, user=Depends(get_current_user)):
    if payload.current_password:
        if not verify_password(payload.current_password, user.get("password_hash", "")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password")

    email = user.get("email")
    otp_doc = await otp_codes_collection().find_one({"email": email, "purpose": "reset_password", "used": False})
    if not otp_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")
    if otp_expired(otp_doc["created_at"]):
        await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired. Request a new code.")

    attempts = int(otp_doc.get("attempts", 0)) + 1
    if attempts > settings.max_otp_attempts:
        await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    if not verify_otp_code(payload.otp_code, otp_doc["code"]):
        await otp_codes_collection().update_one({"_id": otp_doc["_id"]}, {"$set": {"attempts": attempts}})
        remaining = max(settings.max_otp_attempts - attempts, 0)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {remaining} attempts remaining.")

    await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
    await users_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    await invalidate_session(user["_id"])
    return {"success": True}


@router.delete("/me")
async def delete_account(payload: DeleteAccountRequest, user=Depends(get_current_user)):
    if payload.confirm.strip().upper() != "DELETE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type DELETE to confirm.")

    email = user.get("email")
    otp_doc = await otp_codes_collection().find_one({"email": email, "purpose": "delete_account", "used": False})
    if not otp_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")
    if otp_expired(otp_doc["created_at"]):
        await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired. Request a new code.")

    attempts = int(otp_doc.get("attempts", 0)) + 1
    if attempts > settings.max_otp_attempts:
        await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    if not verify_otp_code(payload.otp_code, otp_doc["code"]):
        await otp_codes_collection().update_one({"_id": otp_doc["_id"]}, {"$set": {"attempts": attempts}})
        remaining = max(settings.max_otp_attempts - attempts, 0)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {remaining} attempts remaining.")

    await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
    user_id = user["_id"]
    await users_collection().delete_one({"_id": user_id})
    await sessions_collection().delete_many({"user_id": user_id})
    await vocabulary_collection().delete_many({"user_id": user_id})
    await grammar_stats_collection().delete_many({"user_id": user_id})
    await invalidate_session(user_id)
    return {"success": True}


@router.post("/me/delete/request-otp")
@limiter.limit("3/hour")
async def request_delete_otp(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    email = user.get("email")
    if not allow_otp_request(email):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests. Try again later.")
    record_otp_request(email)

    await otp_codes_collection().delete_many({"email": email, "purpose": "delete_account"})
    code = generate_otp_code()
    await otp_codes_collection().insert_one(
        {
            "email": email,
            "code": hash_otp_code(code),
            "purpose": "delete_account",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "used": False,
        }
    )
    background_tasks.add_task(send_otp_email, email, user.get("username", "there"), code)
    return {"message": "OTP sent to your email"}


@onboarding_router.post("/complete")
async def complete_onboarding(payload: OnboardingRequest, user=Depends(get_current_user)):
    updates = {
        "native_language": payload.native_language,
        "target_language": payload.target_language,
        "goals": payload.goals,
        "tutor_persona": payload.tutor_persona,
        "daily_goal_minutes": payload.daily_goal_minutes,
        "updated_at": datetime.now(timezone.utc),
    }
    await users_collection().update_one({"_id": user["_id"]}, {"$set": updates})
    return {"success": True}


@router.get("/me/stats")
async def get_stats(user=Depends(get_current_user)):
    vocab = vocabulary_collection()
    counts = {
        "new": await vocab.count_documents({"user_id": user["_id"], "status": "new"}),
        "learning": await vocab.count_documents({"user_id": user["_id"], "status": "learning"}),
        "known": await vocab.count_documents({"user_id": user["_id"], "status": "known"}),
        "mastered": await vocab.count_documents({"user_id": user["_id"], "status": "mastered"}),
    }
    total_sessions = await sessions_collection().count_documents({"user_id": user["_id"]})
    return {
        "xp": user.get("xp", 0),
        "streak": user.get("streak", 0),
        "streak_freeze": user.get("streak_freeze", 0),
        "vocabulary": counts,
        "total_sessions": total_sessions,
    }


@router.get("/search")
async def search_users(q: str, user=Depends(get_current_user)):
    cursor = users_collection().find(
        {"$or": [{"username": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]}
    ).limit(10)
    items = []
    async for item in cursor:
        if item["_id"] == user["_id"]:
            continue
        item.pop("password_hash", None)
        item.pop("totp_secret", None)
        item.pop("totp_pending_secret", None)
        item["_id"] = str(item["_id"])
        items.append(item)
    return {"items": items}


@router.post("/friends/request/{friend_id}")
async def request_friend(friend_id: str, user=Depends(get_current_user)):
    await friend_connections_collection().update_one(
        {"requester_id": user["_id"], "receiver_id": ObjectId(friend_id)},
        {"$set": {"status": "pending", "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"success": True}


@router.post("/friends/accept/{friend_id}")
async def accept_friend(friend_id: str, user=Depends(get_current_user)):
    await friend_connections_collection().update_one(
        {"requester_id": ObjectId(friend_id), "receiver_id": user["_id"]},
        {"$set": {"status": "accepted"}},
    )
    await users_collection().update_one({"_id": user["_id"]}, {"$addToSet": {"friends": ObjectId(friend_id)}})
    await users_collection().update_one({"_id": ObjectId(friend_id)}, {"$addToSet": {"friends": user["_id"]}})
    return {"success": True}


@router.delete("/friends/{friend_id}")
async def remove_friend(friend_id: str, user=Depends(get_current_user)):
    await friend_connections_collection().delete_many(
        {"$or": [
            {"requester_id": user["_id"], "receiver_id": ObjectId(friend_id)},
            {"requester_id": ObjectId(friend_id), "receiver_id": user["_id"]},
        ]}
    )
    await users_collection().update_one({"_id": user["_id"]}, {"$pull": {"friends": ObjectId(friend_id)}})
    await users_collection().update_one({"_id": ObjectId(friend_id)}, {"$pull": {"friends": user["_id"]}})
    return {"success": True}


@router.get("/friends")
async def list_friends(user=Depends(get_current_user)):
    cursor = users_collection().find({"_id": {"$in": user.get("friends", [])}})
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item.pop("password_hash", None)
        item.pop("totp_secret", None)
        item.pop("totp_pending_secret", None)
        items.append(item)
    return {"items": items}


@router.post("/challenges/create")
async def create_challenge(payload: ChallengeCreateRequest, user=Depends(get_current_user)):
    doc = {
        "challenger_id": user["_id"],
        "challenged_id": ObjectId(payload.challenged_id),
        "challenge_type": payload.challenge_type,
        "target_value": payload.target_value,
        "start_date": datetime.now(timezone.utc),
        "end_date": datetime.now(timezone.utc),
        "challenger_value": 0,
        "challenged_value": 0,
        "status": "active",
        "winner_id": None,
    }
    result = await challenges_collection().insert_one(doc)
    return {"id": str(result.inserted_id)}


@router.get("/challenges")
async def list_challenges(user=Depends(get_current_user)):
    cursor = challenges_collection().find(
        {"$or": [{"challenger_id": user["_id"]}, {"challenged_id": user["_id"]}]}
    ).sort("start_date", -1)
    items = []
    async for item in cursor:
        item["_id"] = str(item["_id"])
        item["challenger_id"] = str(item["challenger_id"])
        item["challenged_id"] = str(item["challenged_id"])
        if item.get("winner_id"):
            item["winner_id"] = str(item["winner_id"])
        items.append(item)
    return {"items": items}


@router.put("/challenges/{challenge_id}/accept")
async def accept_challenge(challenge_id: str, user=Depends(get_current_user)):
    await challenges_collection().update_one(
        {"_id": ObjectId(challenge_id), "challenged_id": user["_id"]},
        {"$set": {"status": "active", "start_date": datetime.now(timezone.utc)}},
    )
    return {"success": True}


@history_router.get("")
async def list_history(user=Depends(get_current_user), skip: int = 0, limit: int = 20):
    cursor = sessions_collection().find({"user_id": user["_id"]}).sort("started_at", -1).skip(skip).limit(limit)
    items = []
    async for session in cursor:
        session["_id"] = str(session["_id"])
        session["user_id"] = str(session["user_id"])
        items.append(session)
    total = await sessions_collection().count_documents({"user_id": user["_id"]})
    return {"items": items, "total": total}


@history_router.get("/{session_id}")
async def session_detail(session_id: str, user=Depends(get_current_user)):
    session = await sessions_collection().find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session["_id"] = str(session["_id"])
    session["user_id"] = str(session["user_id"])
    return session
