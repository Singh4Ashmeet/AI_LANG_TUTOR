from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..auth import hash_password
from ..models.user import User

ADMIN_EMAIL = "ashmeet.singh.talwar1@gmail.com"
ADMIN_PASSWORD = "0409Ashmeet*"
ADMIN_USERNAME = "Ashmeet"


async def seed_admin(session: AsyncSession) -> None:
    existing_admin = (await session.execute(select(User).where(User.role == "admin"))).scalar_one_or_none()
    if existing_admin:
        return

    now = datetime.utcnow()
    admin = User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL.lower(),
        hashed_password=hash_password(ADMIN_PASSWORD),
        role="admin",
        native_language="english",
        target_language="english",
        cefr_level="C2",
        is_active=True,
        otp_enabled=True,
        onboarding_complete=True,
        created_at=now,
        updated_at=now,
    )
    session.add(admin)
    await session.commit()

