import os
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from sqlalchemy.orm import Session

from app.crud.therapy_words import get_word_by_key
from app.services.voice_service import VoiceService

logger = logging.getLogger("uvicorn.error")

class BaseTTSEngine(ABC):
    @abstractmethod
    def generate_speech(self, text: str, language: str, output_path: Path) -> None:
        """
        Synthesize speech from text in a given language and save it as a WAV file to output_path.
        """
        pass

class CoquiTTSEngine(BaseTTSEngine):
    def generate_speech(self, text: str, language: str, output_path: Path) -> None:
        # Map frontend language code to Coqui-compatible code if necessary
        # Coqui XTTS v2 supports: 'en', 'hi', etc.
        # For unsupported languages, we try to run them or fall back to mock audio
        lang_code = language.strip().lower()
        
        # Ensure underlying Coqui model is loaded
        if VoiceService._tts_model is None:
            logger.info("CoquiTTSEngine: XTTS v2 model not loaded, loading now...")
            VoiceService.load_model()
            
        import torch
        logger.info(f"CoquiTTSEngine: Generating speech for text='{text}' in language='{lang_code}'")
        try:
            with torch.inference_mode():
                # Synthesize text directly to output path
                VoiceService._tts_model.tts_to_file(
                    text=text,
                    language=lang_code,
                    file_path=str(output_path)
                )
            logger.info(f"CoquiTTSEngine: Successfully wrote speech file to {output_path}")
        except Exception as e:
            logger.error(f"CoquiTTSEngine: Speech generation failed: {e}")
            
            # Developer friendly fallback option
            fallback_enabled = os.getenv("TTS_FALLBACK_TO_DUMMY", "true").lower() == "true"
            if fallback_enabled:
                logger.warning(f"CoquiTTSEngine: Fallback is enabled. Generating synthetic placeholder tone for '{text}' ({lang_code})")
                try:
                    import numpy as np
                    import soundfile as sf
                    # Generate a 1-second clean sine tone (440Hz) at 16kHz sample rate
                    sample_rate = 16000
                    duration = 1.0
                    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
                    audio_signal = np.sin(2 * np.pi * 440 * t) * 0.15
                    sf.write(str(output_path), audio_signal, sample_rate)
                    logger.info(f"CoquiTTSEngine: Created synthetic placeholder file at {output_path}")
                    return
                except Exception as dummy_err:
                    logger.error(f"CoquiTTSEngine: Failed to generate fallback audio: {dummy_err}")
            
            raise RuntimeError(f"Speech synthesis failed for language '{lang_code}': {str(e)}")

class AudioService:
    _locks = {}
    _global_lock = threading.Lock()

    def __init__(self, tts_engine: BaseTTSEngine, db: Session):
        self.tts_engine = tts_engine
        self.db = db

    @classmethod
    def get_lock_for(cls, word_key: str, language: str):
        key = (word_key.lower().strip(), language.lower().strip())
        with cls._global_lock:
            if key not in cls._locks:
                cls._locks[key] = threading.Lock()
            return cls._locks[key]

    def get_audio_path(self, word_key: str, language: str) -> Path:
        """
        Returns the absolute Path for the cached audio file.
        Folder: assets/audio/{language}/{word_key}.wav
        """
        # Return path relative to backend directory (working directory of server execution)
        return Path("assets") / "audio" / language.lower().strip() / f"{word_key.lower().strip()}.wav"

    def audio_exists(self, word_key: str, language: str) -> bool:
        """
        Check if the cached audio file already exists on disk.
        """
        return self.get_audio_path(word_key, language).exists()

    def lookup_translation(self, word_key: str, language: str) -> str | None:
        """
        Look up translation for a word key in the database for the given language.
        """
        word = get_word_by_key(self.db, word_key)
        if not word:
            return None
            
        lang_code = language.strip().lower()
        # Map code to column
        lang_col_map = {
            "en": "english",
            "te": "telugu",
            "hi": "hindi",
            "ta": "tamil",
            "kn": "kannada",
            "ml": "malayalam",
            "bn": "bengali",
            "mr": "marathi"
        }
        col_name = lang_col_map.get(lang_code)
        if not col_name:
            return None
        
        val = getattr(word, col_name, None)
        if val and val.strip() != "":
            return val.strip()
        return None

    def generate_audio(self, word_key: str, language: str) -> tuple[Path, bool]:
        """
        Retrieves pronunciation audio. If cached, returns immediately.
        If missing, queries DB for translation and generates it.
        Thread-safe double-check lock prevents duplicate simultaneous generation.
        Returns:
            (audio_path, generated_flag)
        """
        word_key = word_key.lower().strip()
        language = language.lower().strip()
        
        # Fast path check: exists
        if self.audio_exists(word_key, language):
            return self.get_audio_path(word_key, language), False

        # Lock path for this exact word-language combination
        lock = self.get_lock_for(word_key, language)
        with lock:
            # Double-check inside lock
            audio_path = self.get_audio_path(word_key, language)
            if audio_path.exists():
                return audio_path, False

            # Check translation from database
            translated_word = self.lookup_translation(word_key, language)
            target_lang = language

            # Fallback to English if translation is missing
            if not translated_word:
                logger.warning(f"Translation missing for word '{word_key}' in '{language}'. Falling back to English.")
                target_lang = "en"
                translated_word = self.lookup_translation(word_key, "en")
                if not translated_word:
                    # Final fallback: use word key as English text
                    translated_word = word_key

                # Check if the English fallback audio already exists on disk
                fallback_path = self.get_audio_path(word_key, "en")
                if fallback_path.exists():
                    return fallback_path, False
                
                audio_path = fallback_path

            # Create container directory
            audio_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # Generate pronunciation using configured TTS engine
                self.tts_engine.generate_speech(translated_word, target_lang, audio_path)
            except Exception as e:
                logger.error(f"TTS generation failed in AudioService: {e}")
                raise

            return audio_path, True
