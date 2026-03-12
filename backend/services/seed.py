from __future__ import annotations

from datetime import datetime, timezone

from ..auth import hash_password
from ..database import users_collection

ADMIN_EMAIL = "ashmeet.singh.talwar1@gmail.com"
ADMIN_PASSWORD = "0409Ashmeet*"
ADMIN_USERNAME = "Ashmeet"


def _admin_document(now: datetime) -> dict:
    return {
        "username": ADMIN_USERNAME,
        "email": ADMIN_EMAIL.lower(),
        "password_hash": hash_password(ADMIN_PASSWORD),
        "role": "admin",
        "native_language": "en",
        "target_language": "en",
        "enrolled_languages": [],
        "cefr_level": "C2",
        "goals": [],
        "tutor_persona": None,
        "tutor_name": "Sofia",
        "daily_goal_minutes": 10,
        "xp": 0,
        "weekly_xp": 0,
        "total_xp": 0,
        "streak": 0,
        "streak_freeze": 0,
        "streak_freeze_last_used": None,
        "last_session_date": None,
        "hearts": 5,
        "hearts_last_refill": now,
        "gems": 0,
        "path_position": {"section_index": 0, "skill_index": 0, "lesson_index": 0, "exercise_index": 0},
        "crown_levels": {},
        "onboarding_complete": True,
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


async def seed_admin() -> None:
    users = users_collection()
    existing_admin = await users.find_one({"role": "admin"})
    if existing_admin:
        return
    now = datetime.now(timezone.utc)
    await users.insert_one(_admin_document(now))
