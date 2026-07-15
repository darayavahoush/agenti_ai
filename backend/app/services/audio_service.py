from pathlib import Path
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.therapy_words import get_translation_text
from app.services.tts_provider import CoquiTTSProvider
from app.utils.word_utils import normalize_word_key


class AudioService:
    ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
    AUDIO_SUBDIR = ASSETS_DIR / "audio"

    def __init__(self, tts_provider: CoquiTTSProvider | None = None):
        self.tts_provider = tts_provider or CoquiTTSProvider()

    @staticmethod
    def _normalize_language(language: str) -> str:
        if not language or not language.strip():
            return "en"
        return language.strip().lower().split("-")[0]

    def get_word_audio_path(self, word_key: str, language: str, extension: str = ".wav") -> Path:
        safe_key = normalize_word_key(word_key)
        language_code = self._normalize_language(language)
        if not extension.startswith("."):
            extension = f".{extension}"
        return self.AUDIO_SUBDIR / language_code / f"{safe_key}{extension}"

    def get_existing_audio_path(self, word_key: str, language: str) -> Path | None:
        for extension in (".webm", ".wav"):
            candidate = self.get_word_audio_path(word_key, language, extension)
            if candidate.exists():
                return candidate
        return None

    def save_uploaded_audio(self, word_key: str, language: str, file_bytes: bytes, extension: str = ".webm") -> Path:
        audio_path = self.get_word_audio_path(word_key, language, extension)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(file_bytes)
        return audio_path

    def get_or_create_translated_word_audio(
        self,
        db: Session,
        word_key: str,
        language: str,
    ) -> Tuple[Path, bool, str]:
        safe_key = normalize_word_key(word_key)
        if not safe_key:
            raise HTTPException(status_code=400, detail="Invalid word_key.")

        language_code = self._normalize_language(language)
        localized_word = get_translation_text(db, safe_key, language_code)

        existing_audio_path = self.get_existing_audio_path(safe_key, language_code)
        if existing_audio_path is not None:
            return existing_audio_path, False, localized_word or safe_key

        if localized_word is None:
            if language_code == "en":
                raise HTTPException(status_code=404, detail="Assessment word not found.")
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Translation not found for word '{word_key}' in language '{language_code}'. "
                    "Add a stored translation before generating audio."
                ),
            )

        audio_path = self.get_word_audio_path(safe_key, language_code)
        if audio_path.exists():
            return audio_path, False, localized_word

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        self.tts_provider.synthesize(
            text=localized_word,
            output_path=audio_path,
            language_code=language_code,
        )
        return audio_path, True, localized_word
