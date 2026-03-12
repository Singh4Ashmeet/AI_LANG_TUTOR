from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pyotp
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from ..auth import (
    create_access_token,
    create_reset_token,
    create_temp_token,
    decode_reset_token,
    decode_temp_token,
    hash_password,
    verify_password,
)
from ..config import settings
from ..database import otp_codes_collection, users_collection
from ..dependencies import get_current_user
from ..limiters import limiter
from ..models.user import UserResponse
from ..services.email import send_otp_email
from ..services.otp import (
    allow_otp_request,
    allow_resend,
    generate_otp_code,
    hash_otp_code,
    otp_expired,
    record_otp_request,
    record_resend,
    verify_otp_code,
)
from ..services.sessions import create_session, invalidate_session
from ..services.crypto import decrypt_value

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    native_language: str
    target_language: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OtpVerifyRequest(BaseModel):
    code: str


class ResetRequest(BaseModel):
    email: EmailStr


class ResetVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    new_password: str


def serialize_user(user: dict) -> dict:
    user = {**user}
    user.pop("password_hash", None)
    user.pop("totp_secret", None)
    user.pop("totp_pending_secret", None)
    user["_id"] = str(user["_id"])
    return user


def tutor_name_for_language(language: str) -> str:
    mapping = {
        "es": "Sofia",
        "fr": "Lea",
        "ja": "Yuki",
        "ko": "Minji",
        "de": "Lena",
        "it": "Giulia",
        "pt": "Camila",
        "zh": "Mei",
        "ar": "Noor",
        "ru": "Anya",
        "hi": "Aarav",
    }
    return mapping.get(language, "Sofia")


def build_user_document(payload: RegisterRequest, now: datetime) -> dict:
    return {
        "username": payload.username,
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "role": "user",
        "native_language": payload.native_language,
        "target_language": payload.target_language,
        "enrolled_languages": [
            {
                "target": payload.target_language,
                "path_position": {"section_index": 0, "skill_index": 0, "lesson_index": 0, "exercise_index": 0},
                "cefr_level": "A1",
            }
        ],
        "cefr_level": "A1",
        "goals": [],
        "tutor_persona": None,
        "tutor_name": tutor_name_for_language(payload.target_language),
        "daily_goal_minutes": 10,
        "xp": 0,
        "weekly_xp": 0,
        "total_xp": 0,
        "streak": 0,
        "streak_freeze": 0,
        "streak_freeze_last_used": None,
        "last_session_date": None,
        "hearts": settings.max_hearts,
        "hearts_last_refill": now,
        "gems": 0,
        "path_position": {"section_index": 0, "skill_index": 0, "lesson_index": 0, "exercise_index": 0},
        "crown_levels": {},
        "onboarding_complete": False,
        "is_active": True,
        "totp_secret": None,
        "otp_enabled": True,
        "notification_time": "19:00",
        "sounds_enabled": True,
        "theme": "dark",
        "immersion_mode": False,
        "avatar_color": "#58CC02",
        "friends": [],
        "global_rank": None,
        "achievements_earned": [],
        "total_lessons_complete": 0,
        "total_words_learned": 0,
        "total_minutes_practiced": 0,
        "created_at": now,
        "updated_at": now,
    }


async def _extract_temp_token(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_temp_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/register")
async def register(payload: RegisterRequest):
    users = users_collection()
    if await users.find_one({"$or": [{"email": payload.email.lower()}, {"username": payload.username}]}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    now = datetime.now(timezone.utc)
    try:
        doc = build_user_document(payload, now)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    result = await users.insert_one(doc)
    token, jti = create_access_token({"user_id": str(result.inserted_id), "email": payload.email.lower(), "role": "user"})
    await create_session(result.inserted_id, jti, None, None)
    user = await users.find_one({"_id": result.inserted_id})
    return {"access_token": token, "user": serialize_user(user), "role": "user"}


@router.post("/login/credentials")
@limiter.limit("3/hour")
async def login_credentials(payload: LoginRequest, background_tasks: BackgroundTasks):
    email = payload.email.lower()
    if not allow_otp_request(email):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests. Try again later.")
    record_otp_request(email)

    users = users_collection()
    user = await users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended. Contact support.")

    await otp_codes_collection().delete_many({"email": email, "purpose": "login"})
    code = generate_otp_code()
    code_hash = hash_otp_code(code)
    await otp_codes_collection().insert_one(
        {
            "email": email,
            "code": code_hash,
            "purpose": "login",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "used": False,
        }
    )
    background_tasks.add_task(send_otp_email, email, user.get("username", "there"), code)
    temp_token = create_temp_token({"email": email, "purpose": "login", "token_id": str(uuid4())})
    return {"message": "OTP sent to your email", "otp_required": True, "temp_token": temp_token}


@router.post("/login/verify-otp")
async def verify_login_otp(
    payload: OtpVerifyRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    token_payload = await _extract_temp_token(credentials)
    email = token_payload.get("email")
    if token_payload.get("purpose") != "login" or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    otp_doc = await otp_codes_collection().find_one({"email": email, "purpose": "login", "used": False})
    if not otp_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")
    if otp_expired(otp_doc["created_at"]):
        await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired. Request a new code.")

    attempts = int(otp_doc.get("attempts", 0)) + 1
    if attempts > settings.max_otp_attempts:
        await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Request a new code.")

    if not verify_otp_code(payload.code, otp_doc["code"]):
        await otp_codes_collection().update_one({"_id": otp_doc["_id"]}, {"$set": {"attempts": attempts}})
        remaining = max(settings.max_otp_attempts - attempts, 0)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {remaining} attempts remaining.")

    await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
    user = await users_collection().find_one({"email": email})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.get("role") == "admin" and user.get("totp_secret"):
        totp_token = create_temp_token({"user_id": str(user["_id"]), "purpose": "totp"})
        return {"totp_required": True, "temp_token": totp_token, "role": "admin"}

    access_token, jti = create_access_token({"user_id": str(user["_id"]), "email": email, "role": user.get("role")})
    await create_session(user["_id"], jti, request.headers.get("User-Agent"), request.client.host if request.client else None)
    return {"access_token": access_token, "user": serialize_user(user), "role": user.get("role")}


@router.post("/login/resend-otp")
async def resend_login_otp(
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    token_payload = await _extract_temp_token(credentials)
    email = token_payload.get("email")
    token_id = token_payload.get("token_id")
    if token_payload.get("purpose") != "login" or not email or not token_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not allow_resend(token_id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many resends. Please wait.")
    record_resend(token_id)

    await otp_codes_collection().delete_many({"email": email, "purpose": "login"})
    code = generate_otp_code()
    await otp_codes_collection().insert_one(
        {
            "email": email,
            "code": hash_otp_code(code),
            "purpose": "login",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "used": False,
        }
    )
    user = await users_collection().find_one({"email": email})
    background_tasks.add_task(send_otp_email, email, user.get("username", "there"), code)
    return {"message": "OTP sent to your email"}


@router.post("/login/verify-totp")
async def verify_totp(
    payload: OtpVerifyRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    token_payload = await _extract_temp_token(credentials)
    if token_payload.get("purpose") != "totp":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = token_payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await users_collection().find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    secret = user.get("totp_secret")
    if not secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not enabled")

    totp = pyotp.TOTP(decrypt_value(secret))
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")

    access_token, jti = create_access_token({"user_id": str(user["_id"]), "email": user.get("email"), "role": "admin"})
    await create_session(user["_id"], jti, request.headers.get("User-Agent"), request.client.host if request.client else None)
    return {"access_token": access_token, "user": serialize_user(user), "role": "admin"}


@router.post("/password/request-reset")
@limiter.limit("3/hour")
async def request_password_reset(payload: ResetRequest, background_tasks: BackgroundTasks):
    email = payload.email.lower()
    if not allow_otp_request(email):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP requests. Try again later.")
    record_otp_request(email)

    user = await users_collection().find_one({"email": email})
    if user:
        await otp_codes_collection().delete_many({"email": email, "purpose": "reset_password"})
        code = generate_otp_code()
        await otp_codes_collection().insert_one(
            {
                "email": email,
                "code": hash_otp_code(code),
                "purpose": "reset_password",
                "attempts": 0,
                "created_at": datetime.now(timezone.utc),
                "used": False,
            }
        )
        background_tasks.add_task(send_otp_email, email, user.get("username", "there"), code)
    return {"message": "If the account exists, an OTP has been sent."}


@router.post("/password/verify-reset")
async def verify_reset(payload: ResetVerifyRequest):
    email = payload.email.lower()
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

    if not verify_otp_code(payload.code, otp_doc["code"]):
        await otp_codes_collection().update_one({"_id": otp_doc["_id"]}, {"$set": {"attempts": attempts}})
        remaining = max(settings.max_otp_attempts - attempts, 0)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Incorrect code. {remaining} attempts remaining.")

    await otp_codes_collection().delete_one({"_id": otp_doc["_id"]})
    reset_token = create_reset_token({"email": email})
    return {"reset_token": reset_token}


@router.post("/password/reset")
async def reset_password(payload: ResetPasswordRequest, request: Request):
    token = request.headers.get("reset_token") or request.headers.get("Reset-Token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing reset token")
    try:
        token_payload = decode_reset_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token")
    email = token_payload.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token")

    user = await users_collection().find_one({"email": email})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await users_collection().update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    await invalidate_session(user["_id"])
    return {"success": True}


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return serialize_user(user)


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    await invalidate_session(user["_id"])
    return {"success": True}
