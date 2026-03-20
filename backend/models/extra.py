from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlmodel import Field, JSON, SQLModel


class Curriculum(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    language_pair: str = Field(index=True, unique=True)
    sections: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Achievement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    achievement_id: str = Field(index=True, unique=True)
    title: str
    description: str
    icon: str
    xp_reward: int = 0
    condition_type: str = "custom"
    condition_value: int = 0
    rarity: str = "common"


class UserAchievement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    achievement_id: str = Field(index=True)
    earned_at: datetime = Field(default_factory=datetime.utcnow)


class LeaderboardEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    username: str
    avatar_color: str = "#3b82f6"
    weekly_xp: int = 0
    week_start: datetime = Field(index=True)
    rank: int = 0


class WordOfDay(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(index=True)
    language_pair: str = Field(index=True)
    word: str
    translation: str
    part_of_speech: Optional[str] = None
    example_sentence: Optional[str] = None
    example_translation: Optional[str] = None
    audio_cached: bool = False


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    title: str
    message: str
    type: str = "info"
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GrammarStat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    rule: str = Field(index=True, default="unknown")
    language: str = "unknown"
    mastery: float = 0.0
    errors: int = 0
    attempts: int = 0
    last_error_at: datetime = Field(default_factory=datetime.utcnow)


class Story(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    story_id: str = Field(index=True, unique=True)
    user_id: Optional[int] = Field(default=None, index=True)
    language: str = Field(index=True)
    title: str
    content: dict = Field(default_factory=dict, sa_column=Column(JSON))
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FriendConnection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(index=True)
    receiver_id: int = Field(index=True)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Challenge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    challenger_id: int = Field(index=True)
    challenged_id: int = Field(index=True)
    challenge_type: str
    target_value: int
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: datetime = Field(default_factory=datetime.utcnow)
    challenger_value: int = 0
    challenged_value: int = 0
    status: str = "active"
    winner_id: Optional[int] = None

