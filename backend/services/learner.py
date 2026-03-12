from __future__ import annotations

from datetime import datetime, timedelta, timezone

CEFR_THRESHOLDS = {
    "A1": 500,
    "A2": 1500,
    "B1": 3500,
    "B2": 7000,
    "C1": 12000,
    "C2": 10**9,
}


def apply_sm2(item: dict, quality: int) -> dict:
    ease = max(1.3, float(item.get("ease_factor", 2.5)))
    interval = int(item.get("interval_days", 1))
    repetitions = int(item.get("repetitions", 0))

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

    next_review = datetime.now(timezone.utc) + timedelta(days=interval)

    item.update(
        {
            "ease_factor": ease,
            "interval_days": interval,
            "repetitions": repetitions,
            "next_review": next_review,
        }
    )
    return item


def award_xp(
    user: dict,
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

    user["xp"] = int(user.get("xp", 0)) + earned
    old_level = user.get("cefr_level", "A1")
    new_level = old_level
    for level, threshold in CEFR_THRESHOLDS.items():
        if user["xp"] >= threshold:
            new_level = next_level(level)
    user["cefr_level"] = new_level
    leveled_up = new_level != old_level
    return earned, leveled_up, new_level


def next_level(level: str) -> str:
    order = ["A1", "A2", "B1", "B2", "C1", "C2"]
    if level not in order:
        return "A1"
    idx = order.index(level)
    return order[min(idx + 1, len(order) - 1)]


def update_streak(user: dict) -> dict:
    today = datetime.now(timezone.utc).date()
    last_date = user.get("last_session_date")
    last_freeze_used = user.get("streak_freeze_last_used")

    if last_date is not None:
        last_date = last_date.date()
    if last_freeze_used is not None:
        last_freeze_used = last_freeze_used.date()

    if last_date == today:
        return user

    yesterday = today - timedelta(days=1)
    if last_date == yesterday:
        user["streak"] = int(user.get("streak", 0)) + 1
        if user["streak"] % 7 == 0:
            user["streak_freeze"] = min(2, int(user.get("streak_freeze", 0)) + 1)
    else:
        freezes = int(user.get("streak_freeze", 0))
        if freezes > 0 and last_freeze_used != yesterday:
            user["streak_freeze"] = freezes - 1
            user["streak_freeze_last_used"] = today
        else:
            user["streak"] = 1

    user["last_session_date"] = datetime.now(timezone.utc)
    return user
