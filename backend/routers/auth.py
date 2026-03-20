from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from ..auth import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    create_temp_token,
    decode_token,
    hash_password,
    verify_password,
)
from ..database import get_session
from ..dependencies import get_current_user
from ..models.otp import OTPCode
from ..models.user import User, UserCreate
from ..services.crypto import decrypt_value
from ..services.email import EmailDeliveryError, send_otp_email
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
from ..services.seed import seed_admin
from ..services.sessions import create_session, invalidate_session
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/credentials")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyOTPRequest(BaseModel):
    code: str


class VerifyTOTPRequest(BaseModel):
    code: str


class ResetRequest(BaseModel):
    email: EmailStr


class VerifyResetRequest(BaseModel):
    code: str
    email: EmailStr | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str


def serialize_user(user: User) -> dict:
    data = user.model_dump()
    data.pop("hashed_password", None)
    data.pop("totp_secret", None)
    data.pop("totp_pending_secret", None)
    data["_id"] = data.get("id")
    return data


def _otp_email_error_message(exc: EmailDeliveryError) -> str:
    env = (settings.ENVIRONMENT or "").lower()
    if env == "development":
        if exc.reason == "smtp_not_configured":
            return "OTP email is unavailable. Configure GMAIL_ADDRESS and GMAIL_APP_PASSWORD."
        if exc.reason == "smtp_auth_failed":
            return "OTP email login failed. Use a valid Gmail App Password and try again."
    return "Unable to deliver OTP email right now. Please try again shortly."


def _dev_otp_fallback_enabled() -> bool:
    return (settings.ENVIRONMENT or "").lower() == "development" and bool(settings.ENABLE_DEV_OTP_FALLBACK)


async def _create_login_otp(
    session: AsyncSession,
    email: str,
    username: str,
    purpose: str = "login",
) -> str:
    await session.execute(delete(OTPCode).where(OTPCode.email == email, OTPCode.purpose == purpose))
    code = generate_otp_code()
    now = datetime.utcnow()
    session.add(
        OTPCode(
            email=email,
            code_hash=hash_otp_code(code),
            purpose=purpose,
            attempts=0,
            used=False,
            created_at=now,
            expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
    )
    await session.commit()
    try:
        await send_otp_email(email, username, code)
        return "email"
    except EmailDeliveryError:
        if _dev_otp_fallback_enabled():
            otp_doc = (
                await session.execute(
                    select(OTPCode)
                    .where(OTPCode.email == email, OTPCode.purpose == purpose, OTPCode.used == False)
                    .order_by(desc(OTPCode.created_at))
                )
            ).scalars().first()
            if otp_doc:
                otp_doc.code_hash = hash_otp_code(settings.DEV_OTP_BYPASS_CODE)
                otp_doc.attempts = 0
                otp_doc.used = False
                session.add(otp_doc)
                await session.commit()
            return "development_bypass"

        await session.execute(delete(OTPCode).where(OTPCode.email == email, OTPCode.purpose == purpose))
        await session.commit()
        raise


async def _find_active_otp(session: AsyncSession, email: str, purpose: str) -> OTPCode | None:
    stmt = (
        select(OTPCode)
        .where(OTPCode.email == email, OTPCode.purpose == purpose, OTPCode.used == False)
        .order_by(desc(OTPCode.created_at))
    )
    return (await session.execute(stmt)).scalars().first()


@router.post("/register")
async def register(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    await seed_admin(session)
    email = payload.email.lower()
    existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    name_taken = (await session.execute(select(User).where(User.username == payload.username))).scalar_one_or_none()
    if name_taken:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already in use")

    now = datetime.utcnow()
    user = User(
        username=payload.username,
        email=email,
        hashed_password=hash_password(payload.password),
        native_language=payload.native_language or "english",
        target_language=payload.target_language or "spanish",
        role="user",
        onboarding_complete=False,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"message": "Account created successfully"}


@router.post("/login/credentials")
async def login_credentials(
    request: Request,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    email = payload.email.lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended. Contact support.")

    if not allow_otp_request(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Try again later.",
        )
    try:
        delivery_mode = await _create_login_otp(session, email, user.username, purpose="login")
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_otp_email_error_message(exc),
        ) from exc
    record_otp_request(email)

    temp_id = str(uuid.uuid4())
    temp_token = create_temp_token({"email": email, "scope": "login", "tid": temp_id})
    message = "OTP sent to your email" if delivery_mode == "email" else "Development OTP is ready"
    return {
        "message": message,
        "otp_required": True,
        "temp_token": temp_token,
        "delivery_mode": delivery_mode,
    }


@router.post("/login")
async def login_alias(
    request: Request,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    return await login_credentials(request, payload, session)


@router.post("/login/verify-otp")
async def verify_login_otp(
    request: Request,
    payload: VerifyOTPRequest,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
    temp_payload = decode_token(token)
    if not temp_payload or temp_payload.get("type") != "temp" or temp_payload.get("scope") != "login":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token")

    email = str(temp_payload.get("email", "")).lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token payload")

    otp_doc = await _find_active_otp(session, email, "login")
    if not otp_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")
    if otp_expired(otp_doc.created_at) or otp_doc.expires_at < datetime.utcnow():
        await session.execute(delete(OTPCode).where(OTPCode.id == otp_doc.id))
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired. Request a new code.")

    otp_doc.attempts += 1
    if otp_doc.attempts > settings.MAX_OTP_ATTEMPTS:
        await session.execute(delete(OTPCode).where(OTPCode.id == otp_doc.id))
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        )

    if not verify_otp_code(payload.code, otp_doc.code_hash):
        session.add(otp_doc)
        await session.commit()
        remaining = max(settings.MAX_OTP_ATTEMPTS - otp_doc.attempts, 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect code. {remaining} attempts remaining.",
        )

    otp_doc.used = True
    session.add(otp_doc)
    await session.commit()

    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == "admin" and user.otp_enabled and user.totp_secret:
        temp_token = create_temp_token({"sub": str(user.id), "scope": "totp", "tid": str(uuid.uuid4())})
        return {"totp_required": True, "temp_token": temp_token}

    jti = str(uuid.uuid4())
    await create_session(
        session,
        user.id,
        jti,
        request.headers.get("User-Agent"),
        request.client.host if request.client else None,
    )
    access_token = create_access_token({"sub": str(user.id), "jti": jti})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token, "user": serialize_user(user), "role": user.role}


@router.post("/login/resend-otp")
async def resend_login_otp(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
    temp_payload = decode_token(token)
    if not temp_payload or temp_payload.get("type") != "temp":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token")

    tid = temp_payload.get("tid") or token
    if not allow_resend(str(tid)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Resend limit reached")

    email = str(temp_payload.get("email", "")).lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        delivery_mode = await _create_login_otp(session, email, user.username, purpose="login")
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_otp_email_error_message(exc),
        ) from exc
    record_resend(str(tid))
    message = "OTP resent" if delivery_mode == "email" else "Development OTP refreshed"
    return {"message": message, "delivery_mode": delivery_mode}


@router.post("/login/verify-totp")
async def verify_totp(
    request: Request,
    payload: VerifyTOTPRequest,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
    temp_payload = decode_token(token)
    if not temp_payload or temp_payload.get("type") != "temp" or temp_payload.get("scope") != "totp":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid temporary token")

    user_id = int(temp_payload.get("sub", "0"))
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP is not configured")

    secret = decrypt_value(user.totp_secret)
    if not pyotp.TOTP(secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticator code")

    jti = str(uuid.uuid4())
    await create_session(
        session,
        user.id,
        jti,
        request.headers.get("User-Agent"),
        request.client.host if request.client else None,
    )
    access_token = create_access_token({"sub": str(user.id), "jti": jti})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token, "user": serialize_user(user), "role": user.role}


@router.post("/password/request-reset")
async def request_password_reset(
    payload: ResetRequest,
    session: AsyncSession = Depends(get_session),
):
    email = payload.email.lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user and allow_otp_request(email):
        try:
            await _create_login_otp(session, email, user.username, purpose="reset_password")
            record_otp_request(email)
        except EmailDeliveryError:
            pass
    return {"message": "If the account exists, an OTP has been sent."}


@router.post("/password/verify-reset")
async def verify_reset_otp(payload: VerifyResetRequest, session: AsyncSession = Depends(get_session)):
    otp_doc: OTPCode | None = None
    email = payload.email.lower() if payload.email else None

    if email:
        otp_doc = await _find_active_otp(session, email, "reset_password")
    else:
        candidates = (
            await session.execute(
                select(OTPCode)
                .where(OTPCode.purpose == "reset_password", OTPCode.used == False)
                .order_by(desc(OTPCode.created_at))
                .limit(50)
            )
        ).scalars().all()
        for candidate in candidates:
            if verify_otp_code(payload.code, candidate.code_hash):
                otp_doc = candidate
                email = candidate.email
                break

    if not otp_doc or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found. Request a new code.")

    if otp_expired(otp_doc.created_at) or otp_doc.expires_at < datetime.utcnow():
        await session.execute(delete(OTPCode).where(OTPCode.id == otp_doc.id))
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired. Request a new code.")

    otp_doc.attempts += 1
    if otp_doc.attempts > settings.MAX_OTP_ATTEMPTS:
        await session.execute(delete(OTPCode).where(OTPCode.id == otp_doc.id))
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        )

    if not verify_otp_code(payload.code, otp_doc.code_hash):
        session.add(otp_doc)
        await session.commit()
        remaining = max(settings.MAX_OTP_ATTEMPTS - otp_doc.attempts, 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect code. {remaining} attempts remaining.",
        )

    otp_doc.used = True
    session.add(otp_doc)
    await session.commit()
    return {"reset_token": create_reset_token({"email": email})}


@router.post("/password/reset")
async def reset_password(
    payload: ResetPasswordRequest,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
    reset_payload = decode_token(token)
    if not reset_payload or reset_payload.get("type") != "reset":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid reset token")

    email = str(reset_payload.get("email", "")).lower()
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    await session.commit()
    await invalidate_session(session, user.id)
    return {"message": "Password updated successfully"}


@router.get("/me")
async def auth_me(user: User = Depends(get_current_user)):
    return serialize_user(user)


@router.post("/logout")
async def logout(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await invalidate_session(session, user.id)
    return {"status": "success"}
