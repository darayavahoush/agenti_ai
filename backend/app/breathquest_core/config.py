from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BreathQuestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",   # Ignore env vars not defined below
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Lavanya123@localhost:5433/vaaksudhi"

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
    return BreathQuestSettings()(backend) PS C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend> python setup_vosk_models.py hi
🎤 Vosk Model Setup for Indian Languages
==================================================
📁 Models directory: C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend\vosk_models    

📋 Available models:
  hi: Hindi (Devanagari script)
  te: Telugu (Telugu script)
  kn: Kannada (Kannada script)
  ta: Tamil (Tamil script)
  ml: Malayalam (Malayalam script)
  bn: Bengali (Bengali script)
  mr: Marathi (Devanagari script)
  en: English (US)

💡 Usage:
  python setup_vosk_models.py hi      # Install Hindi model
  python setup_vosk_models.py te      # Install Telugu model
  python setup_vosk_models.py kn      # Install Kannada model
  python setup_vosk_models.py all     # Install all models

🎯 Installing hi model...
✅ Model already exists: vosk-model-hi-0.22
✅ Successfully installed hi model

✨ Setup complete!
📁 Models installed in: C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend\vosk_models 
(backend) PS C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend> python setup_vosk_models.py te 
🎤 Vosk Model Setup for Indian Languages
==================================================
📁 Models directory: C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend\vosk_models    

📋 Available models:
  hi: Hindi (Devanagari script)
  te: Telugu (Telugu script)
  kn: Kannada (Kannada script)
  ta: Tamil (Tamil script)
  ml: Malayalam (Malayalam script)
  bn: Bengali (Bengali script)
  mr: Marathi (Devanagari script)
  en: English (US)

💡 Usage:
  python setup_vosk_models.py hi      # Install Hindi model
  python setup_vosk_models.py te      # Install Telugu model
  python setup_vosk_models.py kn      # Install Kannada model
  python setup_vosk_models.py all     # Install all models

🎯 Installing te model...
📥 Downloading from: https://alphacephei.com/vosk/models/vosk-model-te-0.22.zip

❌ Download failed: HTTP Error 404: Not Found
❌ Failed to install te model

✨ Setup complete!
📁 Models installed in: C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend\vosk_models 
(backend) PS C:\Users\lavan\speak_easy\agentic_AI\vaaksudhi\backend> 