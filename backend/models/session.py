from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        return _handler(ObjectId)


class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime
    errors: List[dict] = []
    new_vocabulary: List[str] = []


class Session(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    session_type: str
    scenario: Optional[str] = None
    messages: List[Message] = []
    xp_earned: int = 0
    duration_seconds: int = 0
    grammar_errors_count: int = 0
    vocabulary_added_count: int = 0
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
