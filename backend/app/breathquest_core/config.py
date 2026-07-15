from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BreathQuestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",   # Ignore env vars not defined below
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Lavanya123@localhost:5432/vaaksudhi"

    # JWT
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Kid session tokens
    KID_TOKEN_EXPIRE_DAYS: int = 30

    # App
    APP_NAME: str = "BreathQuest"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@lru_cache
def get_breathquest_settings() -> BreathQuestSettings:
    return BreathQuestSettings()