from abc import ABC, abstractmethod
from pathlib import Path
from fastapi import HTTPException

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path, language_code: str) -> None:
        raise NotImplementedError

class CoquiTTSProvider(TTSProvider):
    """Compatibility placeholder; no Coqui package is imported."""
    def synthesize(self, text: str, output_path: Path, language_code: str) -> None:
        raise HTTPException(status_code=503, detail="Audio is not cached and no TTS provider is configured.")
