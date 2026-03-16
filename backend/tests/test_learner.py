import pytest
from datetime import datetime, timedelta, timezone
from backend.services.learner import update_streak, award_xp

def test_award_xp_no_level_up():
    user = {"xp": 100, "cefr_level": "A1"}
    earned, leveled_up, new_level = award_xp(user, base=50)
    
    assert earned == 50
    assert leveled_up is False
    assert user["xp"] == 150
    assert user["cefr_level"] == "A1"

def test_award_xp_level_up():
    user = {"xp": 480, "cefr_level": "A1"}
    earned, leveled_up, new_level = award_xp(user, base=50)
    
    assert earned == 50
    assert leveled_up is True
    assert new_level == "A2"
    assert user["xp"] == 530
    assert user["cefr_level"] == "A2"

def test_update_streak_same_day():
    today = datetime.now(timezone.utc)
    user = {
        "streak": 5,
        "last_session_date": today
    }
    updated_user = update_streak(user)
    assert updated_user["streak"] == 5

def test_update_streak_next_day():
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    user = {
        "streak": 5,
        "last_session_date": yesterday
    }
    updated_user = update_streak(user)
    assert updated_user["streak"] == 6

def test_update_streak_lost():
    long_ago = datetime.now(timezone.utc) - timedelta(days=3)
    user = {
        "streak": 5,
        "last_session_date": long_ago,
        "streak_freeze": 0
    }
    updated_user = update_streak(user)
    assert updated_user["streak"] == 1
