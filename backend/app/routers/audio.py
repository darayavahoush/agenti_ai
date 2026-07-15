from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.database import SessionLocal
from app.services.audio_service import AudioService, CoquiTTSEngine

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/api", tags=["Audio Service"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Shared singleton/instantiated engines
tts_engine = CoquiTTSEngine()

@router.get("/audio/{word_key}")
def get_audio(word_key: str, language: str = "en", db: Session = Depends(get_db)):
    """
    Get the pronunciation audio URL for a therapy word.
    If the audio is not already cached, it is generated on the fly.
    """
    if not word_key or not word_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Word key is required"
        )
        
    audio_service = AudioService(tts_engine, db)
    try:
        audio_path, generated = audio_service.generate_audio(word_key, language)
        
        # Construct the response URL
        # e.g. /assets/audio/te/apple.wav
        # If fallback occurred, audio_path will point to /assets/audio/en/apple.wav
        # Let's ensure the path is returned in web format (using forward slashes)
        web_path = "/" + str(audio_path).replace("\\", "/")
        
        return {
            "audio_url": web_path,
            "generated": generated
        }
    except ValueError as ve:
        logger.error(f"Validation error generating audio for '{word_key}' in '{language}': {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Server error generating audio for '{word_key}' in '{language}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate pronunciation: {str(e)}"
        )

@router.get("/words/{word_key}")
def get_localized_word(word_key: str, language: str = "en", db: Session = Depends(get_db)):
    """
    Get the localized translation of a therapy word from the database.
    If the translation is missing, it falls back to the English translation.
    """
    if not word_key or not word_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Word key is required"
        )
        
    audio_service = AudioService(tts_engine, db)
    localized_word = audio_service.lookup_translation(word_key, language)
    
    # If not found, fallback to English
    if not localized_word:
        logger.warning(f"Localized word translation missing for '{word_key}' in '{language}'. Falling back to English.")
        localized_word = audio_service.lookup_translation(word_key, "en")
        if not localized_word:
            localized_word = word_key # Default to the key itself
            
    return {
        "word_key": word_key.lower().strip(),
        "language": language.lower().strip(),
        "localized_word": localized_word
    }
