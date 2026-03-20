from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class OTPCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    code_hash: str
    purpose: str = Field(index=True)
    attempts: int = 0
    used: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    expires_at: datetime

