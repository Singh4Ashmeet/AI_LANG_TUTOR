from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from secrets import randbelow

from passlib.context import CryptContext

from ..config import settings

_otp_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_otp_request_log: dict[str, list[datetime]] = defaultdict(list)
_resend_counts: dict[str, int] = {}


def generate_otp_code() -> str:
    return f"{randbelow(1_000_000):06d}"


def hash_otp_code(code: str) -> str:
    return _otp_context.hash(code)


def verify_otp_code(code: str, code_hash: str) -> bool:
    return _otp_context.verify(code, code_hash)


def otp_expired(created_at: datetime) -> bool:
    return created_at + timedelta(minutes=settings.otp_expire_minutes) < datetime.now(timezone.utc)


def allow_otp_request(email: str) -> bool:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    recent = [ts for ts in _otp_request_log[email] if ts >= window_start]
    _otp_request_log[email] = recent
    return len(recent) < 3


def record_otp_request(email: str) -> None:
    _otp_request_log[email].append(datetime.now(timezone.utc))


def allow_resend(token_id: str) -> bool:
    return _resend_counts.get(token_id, 0) < 3


def record_resend(token_id: str) -> None:
    _resend_counts[token_id] = _resend_counts.get(token_id, 0) + 1
