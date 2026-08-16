from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5433/vaaksudhi",
        description="PostgreSQL database connection string"
    )
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    
    # CORS Configuration
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # OpenAI API (optional, for enhanced features)
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key for enhanced features")

    # JWT Configuration (for verifying BreathQuest issued tokens)
    SECRET_KEY: str = Field(default="supersecretkey", description="JWT secret key")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")

    # Email (OTP verification) -- Gmail SMTP with an app password. Ported
    # 2026-08-12 alongside verify.py, which was never mounted in main.py
    # because it still had quest-games' standalone-layout imports.
    SMTP_HOST: str = Field(default="", description="SMTP host for sending OTP emails")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USER: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password (app password for Gmail)")

    # Phone (OTP verification) -- Azure Communication Services (ACS) SMS,
    # matching Azure hosting. Mirrors the SMTP block above: empty by
    # default means dev/local, and phone_provider.py's real implementation
    # falls back to logging the code instead of sending, same as
    # send_otp_email does for SMTP.
    #
    # AZURE_COMMUNICATION_CONNECTION_STRING is the full connection string
    # from the ACS resource's "Keys" blade in the Azure portal (contains
    # both the endpoint and the access key, so this one field is all
    # that's needed for auth -- unlike Twilio's separate SID/token pair).
    AZURE_COMMUNICATION_CONNECTION_STRING: str = Field(default="", description="ACS resource connection string, from Keys blade in Azure portal")
    AZURE_COMMUNICATION_FROM_NUMBER: str = Field(default="", description="ACS phone number to send OTP SMS from, E.164 format e.g. +15551234567")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

# For backward compatibility
DATABASE_URL = settings.DATABASE_URL