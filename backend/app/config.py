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
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

# For backward compatibility
DATABASE_URL = settings.DATABASE_URL