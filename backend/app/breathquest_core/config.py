from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BreathQuestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:Lavanya123@localhost:5433/vaaksudhi"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    KID_TOKEN_EXPIRE_DAYS: int = 30
    # OAuth client ID from Google Cloud Console (Web application type).
    # Used server-side to verify the `aud` claim on every Google ID token
    # we're handed, so a token minted for a different app can't be replayed
    # here. Empty by default so a misconfigured deploy fails loudly (see
    # google_oauth.py) rather than silently accepting any Google token.
    GOOGLE_CLIENT_ID: str = ""
    # Set to true only once a real payment provider (Razorpay/Stripe) is
    # wired into billing_provider.py. While false, billing.py's checkout
    # endpoints are allowed to free-grant subscriptions (see _mark_active's
    # comment) since there's no paywall to enforce yet. Flipping this to
    # true and leaving _mark_active's free-grant path in place is a bug --
    # it should be swapped for the real provider call in the same change.
    PAYMENTS_LIVE: bool = False
    APP_NAME: str = "BreathQuest"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@lru_cache
def get_breathquest_settings() -> BreathQuestSettings:
    return BreathQuestSettings()