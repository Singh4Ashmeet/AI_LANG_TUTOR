from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        return _handler(ObjectId)


class AdminLog(BaseModel):
    id: str = Field(alias="_id")
    event_type: str
    message: str
    metadata: dict[str, Any] = {}
    admin_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class AdminStats(BaseModel):
    total_users: int = 0
    active_today: int = 0
    active_week: int = 0
    new_registrations: int = 0
    total_sessions: int = 0
    sessions_today: int = 0
