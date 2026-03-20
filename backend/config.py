from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "LinguAI"
    VERSION: str = "0.3.0"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    TEMP_TOKEN_EXPIRE_MINUTES: int = 10
    RESET_TOKEN_EXPIRE_MINUTES: int = 15
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    FRONTEND_URL: str = "http://localhost:5173"

    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    WHISPER_MODEL: str = "base"

    MAX_HEARTS: int = 5
    HEARTS_REFILL_HOURS: int = 1
    MAX_OTP_ATTEMPTS: int = 3
    OTP_EXPIRE_MINUTES: int = 10

    GMAIL_ADDRESS: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None
    DEV_OTP_BYPASS_CODE: str = "000000"
    ENABLE_DEV_OTP_FALLBACK: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
