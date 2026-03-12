from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize_password(password: str) -> str:
    # bcrypt only supports 72 bytes; enforce a hard limit to avoid runtime errors.
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password too long (max 72 bytes).")
    return password


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password), rounds=12)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _create_token(payload: dict, expires_delta: timedelta, token_type: str) -> tuple[str, dict]:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = payload.copy()
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm), to_encode


def create_access_token(payload: dict) -> tuple[str, str]:
    jti = str(uuid4())
    token, encoded = _create_token(
        {**payload, "jti": jti},
        timedelta(days=settings.access_token_expire_days),
        "access",
    )
    return token, encoded["jti"]


def create_temp_token(payload: dict) -> str:
    token, _ = _create_token(
        payload,
        timedelta(minutes=settings.temp_token_expire_minutes),
        "temp",
    )
    return token


def create_reset_token(payload: dict) -> str:
    token, _ = _create_token(
        payload,
        timedelta(minutes=settings.reset_token_expire_minutes),
        "reset",
    )
    return token


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def decode_access_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise ValueError("Invalid token")
    return payload


def decode_temp_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("type") != "temp":
        raise ValueError("Invalid token")
    return payload


def decode_reset_token(token: str) -> dict:
    payload = _decode_token(token)
    if payload.get("type") != "reset":
        raise ValueError("Invalid token")
    return payload
