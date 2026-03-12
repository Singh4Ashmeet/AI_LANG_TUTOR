from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        return _handler(ObjectId)


class VocabularyItem(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
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
    source_session_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
