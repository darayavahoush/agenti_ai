from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas.audio import AudioResponse
from app.services.audio_service import AudioService
from app.utils.word_utils import normalize_word_key

router = APIRouter(prefix="/audio", tags=["Audio"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/words/{word_key}", response_model=AudioResponse)
def get_word_audio(
    word_key: str,
    language: str = Query("en-IN", description="Language code like en-IN, hi-IN, ta-IN, te-IN, bn-IN, mr-IN"),
    db: Session = Depends(get_db),
):
    normalized_key = normalize_word_key(word_key)
    if not normalized_key:
        raise HTTPException(status_code=400, detail="Invalid word_key.")

    audio_service = AudioService()
    audio_path, generated, localized_word = audio_service.get_or_create_translated_word_audio(
        db=db,
        word_key=normalized_key,
        language=language,
    )

    try:
        relative_path = audio_path.relative_to(audio_service.ASSETS_DIR).as_posix()
    except Exception:
        relative_path = audio_path.name

    return AudioResponse(
        audio_url=f"/assets/{relative_path}",
        generated=generated,
        localized_word=localized_word,
    )


@router.get("/words/{word_key}/exists")
def audio_exists(
    word_key: str,
    language: str = Query("en-IN", description="Language code like en-IN, hi-IN, ta-IN, te-IN, bn-IN, mr-IN"),
):
    normalized_key = normalize_word_key(word_key)
    if not normalized_key:
        raise HTTPException(status_code=400, detail="Invalid word_key.")

    audio_service = AudioService()
    audio_path = audio_service.get_existing_audio_path(normalized_key, language)
    if audio_path is None:
        return {"exists": False, "audio_url": None}

    try:
        relative_path = audio_path.relative_to(audio_service.ASSETS_DIR).as_posix()
    except Exception:
        relative_path = audio_path.name

    return {"exists": True, "audio_url": f"/assets/{relative_path}"}


@router.post("/words/{word_key}", status_code=status.HTTP_201_CREATED)
async def save_uploaded_word_audio(
    word_key: str,
    file: UploadFile = File(...),
    language: str = Query("en-IN", description="Language code like en-IN, hi-IN, ta-IN, te-IN, bn-IN, mr-IN"),
):
    normalized_key = normalize_word_key(word_key)
    if not normalized_key:
        raise HTTPException(status_code=400, detail="Invalid word_key.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    audio_service = AudioService()
    file_bytes = await file.read()
    extension = Path(file.filename).suffix.lower() or ".webm"
    if extension not in {".wav", ".webm", ".mp3", ".m4a", ".ogg", ".oga", ".mp4"}:
        extension = ".webm"

    audio_path = audio_service.save_uploaded_audio(normalized_key, language, file_bytes, extension=extension)

    try:
        relative_path = audio_path.relative_to(audio_service.ASSETS_DIR).as_posix()
    except Exception:
        relative_path = audio_path.name

    return {
        "audio_url": f"/assets/{relative_path}",
        "generated": False,
        "localized_word": None,
    }
