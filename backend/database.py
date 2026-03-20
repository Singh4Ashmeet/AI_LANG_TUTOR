from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from .config import settings

# Import all models here to register them
from .models.user import User
from .models.vocabulary import VocabularyItem
from .models.admin import AdminLog
from .models.session import Session
from .models.active_session import ActiveSession
from .models.revoked_token import RevokedToken
from .models.otp import OTPCode
from .models.extra import Curriculum, Achievement, UserAchievement, LeaderboardEntry, WordOfDay, Notification, GrammarStat, Story, FriendConnection, Challenge

# Async engine for asyncpg
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Optional
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
