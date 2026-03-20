from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from secrets import randbelow
import bcrypt

_otp_request_log: dict[str, list[datetime]] = defaultdict(list)
_resend_counts: dict[str, int] = {}

def generate_otp_code() -> str:
    return f"{randbelow(1_000_000):06d}"

def hash_otp_code(code: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(code.encode('utf-8'), salt).decode('utf-8')

def verify_otp_code(code: str, code_hash: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode('utf-8'), code_hash.encode('utf-8'))
    except Exception:
        return False

def otp_expired(created_at: datetime) -> bool:
    # Check if otp_expire_minutes exists in settings, default to 5 if not
    from ..config import settings
    expire_minutes = getattr(settings, 'OTP_EXPIRE_MINUTES', 5)
    return created_at + timedelta(minutes=expire_minutes) < datetime.utcnow()

def allow_otp_request(email: str) -> bool:
    now = datetime.utcnow()
    window_start = now - timedelta(hours=1)
    recent = [ts for ts in _otp_request_log[email] if ts >= window_start]
    _otp_request_log[email] = recent
    return len(recent) < 3

def record_otp_request(email: str) -> None:
    _otp_request_log[email].append(datetime.utcnow())

def allow_resend(token_id: str) -> bool:
    return _resend_counts.get(token_id, 0) < 3

def record_resend(token_id: str) -> None:
    _resend_counts[token_id] = _resend_counts.get(token_id, 0) + 1
