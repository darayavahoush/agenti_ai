"""
Flashcards' own settings, namespaced separately from agenti_ai's app/config.py
so ported thresholds (scoring weights, pass/retry cutoffs, whisper model
choice) don't collide with or get overridden by the rest of the app.
"""
from pydantic_settings import BaseSettings
from typing import Optional

class FlashcardSettings(BaseSettings):
    WHISPER_MODEL: str = "medium"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    TARGET_RMS_MIN: float = 0.02
    TARGET_RMS_MAX: float = 0.15
    TARGET_RATE_MIN: float = 2.0
    TARGET_RATE_MAX: float = 3.5
    SCORE_PASS: int = 80
    SCORE_RETRY: int = 60
    SCORE_SIMPLIFY: int = 40
    SCORE_SUPPORT: int = 20
    MAX_ATTEMPTS: int = 3
    WEIGHTS: dict = {
        "autism":        {"phoneme": 0.65, "loudness": 0.10, "pitch": 0.10, "rate": 0.08, "voice_quality": 0.07},
        "articulation":  {"phoneme": 0.75, "loudness": 0.06, "pitch": 0.05, "rate": 0.07, "voice_quality": 0.07},
        "stuttering":    {"phoneme": 0.40, "loudness": 0.08, "pitch": 0.10, "rate": 0.30, "voice_quality": 0.12},
        "seizure_meds":  {"phoneme": 0.60, "loudness": 0.10, "pitch": 0.10, "rate": 0.12, "voice_quality": 0.08},
    }
    ESPEAK_VOICE: str = "en-in"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = FlashcardSettings()
