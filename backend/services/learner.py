from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any

CEFR_THRESHOLDS = {
    # Lower-bound XP required to hold each CEFR level.
    "A1": 0,
    "A2": 500,
    "B1": 1500,
    "B2": 3500,
    "C1": 7000,
    "C2": 10**9,
}

def apply_sm2(item: Any, quality: int) -> Any:
    # Works with both SQLModel objects and dicts
    ease = getattr(item, "ease_factor", 2.5) if hasattr(item, "ease_factor") else item.get("ease_factor", 2.5)
    interval = getattr(item, "interval_days", 1) if hasattr(item, "interval_days") else item.get("interval_days", 1)
    repetitions = getattr(item, "repetitions", 0) if hasattr(item, "repetitions") else item.get("repetitions", 0)

    ease = max(1.3, float(ease))
    interval = int(interval)
    repetitions = int(repetitions)

    if quality <= 2:
        repetitions = 0
        interval = 1
    elif quality == 3:
        ease = max(1.3, ease - 0.15)
    elif quality == 4:
        interval = max(1, int(interval * ease))
        ease = ease + 0.05
        repetitions += 1
    elif quality >= 5:
        interval = max(1, int(interval * ease * 1.3))
        ease = ease + 0.1
        repetitions += 1

    next_review = datetime.utcnow() + timedelta(days=interval)

    if hasattr(item, "ease_factor"):
        item.ease_factor = ease
        item.interval_days = interval
        item.repetitions = repetitions
        item.next_review = next_review
    else:
        item.update({
            "ease_factor": ease,
            "interval_days": interval,
            "repetitions": repetitions,
            "next_review": next_review,
        })
    return item

def award_xp(
    user: Any,
    base: int,
    vocab_bonus: int = 0,
    zero_errors_bonus: bool = False,
    first_session_bonus: bool = False,
    streak_bonus: int = 0,
) -> tuple[int, bool, str]:
    earned = base + min(vocab_bonus, 30)
    if zero_errors_bonus:
        earned += 15
    if first_session_bonus:
        earned += 5
    earned += streak_bonus

    current_xp = getattr(user, "xp", 0) if hasattr(user, "xp") else user.get("xp", 0)
    new_xp = int(current_xp) + earned
    
    if hasattr(user, "xp"):
        user.xp = new_xp
    else:
        user["xp"] = new_xp

    old_level = getattr(user, "cefr_level", "A1") if hasattr(user, "cefr_level") else user.get("cefr_level", "A1")
    new_level = old_level
    
    target_level = "A1"
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        if new_xp >= CEFR_THRESHOLDS.get(level, 0):
            target_level = level
        else:
            break
    
    new_level = target_level
    if hasattr(user, "cefr_level"):
        user.cefr_level = new_level
    else:
        user["cefr_level"] = new_level
        
    leveled_up = new_level != old_level
    return earned, leveled_up, new_level

def update_streak(user: Any) -> Any:
    today = datetime.utcnow().date()
    last_date = getattr(user, "last_session_date", None) if hasattr(user, "last_session_date") else user.get("last_session_date")
    
    # Handle both datetime and None
    if isinstance(last_date, datetime):
        last_date_only = last_date.date()
    else:
        last_date_only = None

    if last_date_only == today:
        return user

    yesterday = today - timedelta(days=1)
    current_streak = getattr(user, "streak", 0) if hasattr(user, "streak") else user.get("streak", 0)
    
    if last_date_only == yesterday:
        new_streak = int(current_streak) + 1
        if hasattr(user, "streak"):
            user.streak = new_streak
        else:
            user["streak"] = new_streak
    else:
        # Check for streak freeze if implemented, otherwise reset
        if hasattr(user, "streak"):
            user.streak = 1
        else:
            user["streak"] = 1

    now = datetime.utcnow()
    if hasattr(user, "last_session_date"):
        user.last_session_date = now
    else:
        user["last_session_date"] = now
        
    return user
