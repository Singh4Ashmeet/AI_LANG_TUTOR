from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_days: int = 7
    temp_token_expire_minutes: int = 10
    reset_token_expire_minutes: int = 15
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    whisper_model: str = "base"
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    max_otp_attempts: int = 3
    otp_expire_minutes: int = 10
    max_hearts: int = 5
    hearts_refill_hours: int = 1

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[1] / ".env"),
        "extra": "ignore",
    }


settings = Settings()


class AppInfo(BaseModel):
    name: str = "LinguAI"
    version: str = "0.1.0"
