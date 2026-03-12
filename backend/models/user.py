from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        return _handler(ObjectId)


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"
    native_language: Optional[str] = None
    target_language: Optional[str] = None
    enrolled_languages: List[dict] = []
    cefr_level: str = "A1"
    goals: List[str] = []
    tutor_persona: Optional[str] = None
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
    path_position: Optional[dict] = None
    crown_levels: dict = {}
    onboarding_complete: bool = False
    is_active: bool = True
    otp_enabled: bool = True
    notification_time: str = "19:00"
    sounds_enabled: bool = True
    theme: str = "dark"
    immersion_mode: bool = False
    avatar_color: Optional[str] = None
    friends: List[PyObjectId] = []
    global_rank: Optional[int] = None
    achievements_earned: List[str] = []
    total_lessons_complete: int = 0
    total_words_learned: int = 0
    total_minutes_practiced: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    native_language: str
    target_language: str


class UserResponse(UserBase):
    id: str = Field(alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
