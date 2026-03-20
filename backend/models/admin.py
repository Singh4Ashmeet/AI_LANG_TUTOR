from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from sqlmodel import SQLModel, Field, JSON, Column

class AdminLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)
    message: str
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    admin_id: Optional[int] = None
    user_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AdminStats(SQLModel):
    total_users: int = 0
    active_today: int = 0
    active_week: int = 0
    new_registrations: int = 0
    total_sessions: int = 0
    sessions_today: int = 0
