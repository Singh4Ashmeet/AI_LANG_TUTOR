from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column
from sqlmodel import Field, JSON, SQLModel


class SessionExercise(SQLModel):
    type: str
    content: Optional[str] = None
    user_answer: Any = None
    correct_answer: Any = None
    is_correct: Optional[bool] = None
    time_ms: Optional[int] = None


class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_type: str = Field(index=True)
    skill_id: Optional[str] = None
    lesson_index: Optional[int] = None
    scenario: Optional[str] = None

    messages: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    exercises: list[dict] = Field(default_factory=list, sa_column=Column(JSON))

    xp_earned: int = 0
    accuracy_percent: int = 0
    hearts_lost: int = 0
    duration_seconds: int = 0
    grammar_errors_count: int = 0
    vocabulary_added_count: int = 0
    summary: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    coach_tip: Optional[str] = None

    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

