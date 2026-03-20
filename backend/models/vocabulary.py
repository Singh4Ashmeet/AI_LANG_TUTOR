from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class VocabularyItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    word: str
    translation: str
    language: str
    status: str = "new"
    ease_factor: float = 2.5
    interval_days: int = 1
    repetitions: int = 0
    next_review: datetime
    last_seen: Optional[datetime] = None
    times_seen: int = 0
    times_correct: int = 0
    context_sentence: Optional[str] = None
    source_session_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
