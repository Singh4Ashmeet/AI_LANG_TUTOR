from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import Column
from sqlmodel import Field, JSON, SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    role: str = Field(default="user", index=True)

    native_language: Optional[str] = None
    target_language: Optional[str] = None
    cefr_level: str = "A1"
    tutor_persona: Optional[str] = "friendly"
    tutor_name: Optional[str] = None
    daily_goal_minutes: int = 10

    xp: int = 0
    weekly_xp: int = 0
    total_xp: int = 0
    streak: int = 0
    streak_freeze: int = 0
    streak_freeze_last_used: Optional[datetime] = None
    last_session_date: Optional[datetime] = None
    hearts: int = 5
    hearts_last_refill: Optional[datetime] = None
    gems: int = 0

    path_position: dict = Field(
        default_factory=lambda: {
            "section_index": 0,
            "skill_index": 0,
            "lesson_index": 0,
            "exercise_index": 0,
        },
        sa_column=Column(JSON),
    )
    crown_levels: dict = Field(default_factory=dict, sa_column=Column(JSON))
    enrolled_languages: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    goals: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    friends: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    achievements_earned: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    onboarding_complete: bool = False
    is_active: bool = True
    otp_enabled: bool = True
    totp_secret: Optional[str] = None
    totp_pending_secret: Optional[str] = None

    notification_time: str = "19:00"
    sounds_enabled: bool = True
    theme: str = "dark"
    immersion_mode: bool = False
    avatar_color: str = "#3b82f6"

    global_rank: Optional[int] = None
    total_lessons_complete: int = 0
    total_words_learned: int = 0
    total_minutes_practiced: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str


class UserCreate(SQLModel):
    username: str
    email: EmailStr
    password: str
    native_language: Optional[str] = "english"
    target_language: Optional[str] = "spanish"


class UserResponse(UserBase):
    id: int

