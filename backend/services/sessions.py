from __future__ import annotations
from datetime import datetime, timezone
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.active_session import ActiveSession

async def invalidate_session(session: AsyncSession, user_id: int) -> None:
    statement = (
        update(ActiveSession)
        .where(ActiveSession.user_id == user_id)
        .where(ActiveSession.is_valid == True)
        .values(is_valid=False)
    )
    await session.execute(statement)
    await session.commit()

async def create_session(session: AsyncSession, user_id: int, jti: str, device_info: str | None, ip_address: str | None) -> None:
    # First, invalidate existing sessions
    await invalidate_session(session, user_id)
    
    # Check if a session record already exists for this user to update it, or create new one
    statement = select(ActiveSession).where(ActiveSession.user_id == user_id)
    result = await session.execute(statement)
    db_session = result.scalar_one_or_none()
    
    now = datetime.utcnow()
    if db_session:
        db_session.session_token_id = jti
        db_session.device_info = device_info
        db_session.ip_address = ip_address
        db_session.created_at = now
        db_session.last_active = now
        db_session.is_valid = True
        session.add(db_session)
    else:
        new_session = ActiveSession(
            user_id=user_id,
            session_token_id=jti,
            device_info=device_info,
            ip_address=ip_address,
            created_at=now,
            last_active=now,
            is_valid=True
        )
        session.add(new_session)
    
    await session.commit()

async def validate_session(session: AsyncSession, user_id: int, jti: str) -> bool:
    statement = select(ActiveSession).where(
        ActiveSession.user_id == user_id,
        ActiveSession.session_token_id == jti,
        ActiveSession.is_valid == True
    )
    result = await session.execute(statement)
    db_session = result.scalar_one_or_none()
    
    if not db_session:
        return False
    
    db_session.last_active = datetime.utcnow()
    session.add(db_session)
    await session.commit()
    return True
