"""
Flashcards — standalone kid-facing practice block, separate from the 4 games.

Reuses the same kid JWT everything else uses (BreathQuest issues it at
login, get_current_patient_id here just decodes/validates it) so kids
don't get a second login just for this section.
"""
import tempfile
import os
import uuid
import json
import random
import base64
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.vaakmirror_auth import get_current_patient_id
from app.database import get_db

from .tts import speak as tts_speak, get_characters
from .matcher import get_image_for_phrase
from .processor import analyse_audio
from .scorer import build_attempt_result
from .grapheme_to_phoneme import get_phonemes
from . import themes as themes_module
from . import mastery

_DATA_DIR = Path(__file__).resolve().parents[3] / 'data' / 'flashcard_images'
_INDEX_PATH = _DATA_DIR / 'index.json'

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


def _word_payload(word: str, language: str) -> dict:
    with open(_INDEX_PATH) as f:
        index = json.load(f)
    image_path = _DATA_DIR / index[word]
    image_b64 = base64.b64encode(image_path.read_bytes()).decode() if image_path.exists() else None
    return {
        "word": word,
        "language": language,
        "theme": themes_module.theme_for_word(word),
        "phonemes": get_phonemes(word, language),
        "image_base64": image_b64,
    }


@router.get("/themes")
def list_themes(patient_id: str = Depends(get_current_patient_id)):
    return {"themes": themes_module.list_themes()}


@router.get("/words")
def words_for_theme(theme: str, patient_id: str = Depends(get_current_patient_id)):
    return {"theme": theme, "words": themes_module.words_for_theme(theme)}


@router.get("/random-word")
def random_word(
    language: str = "english",
    theme: str = None,
    word: str = None,
    patient_id: str = Depends(get_current_patient_id),
):
    with open(_INDEX_PATH) as f:
        index = json.load(f)

    # Exact word requested (card-level selection). Falls through to
    # theme/full-random only if the word somehow isn't in the index.
    if word and word in index:
        return _word_payload(word, language)

    if theme:
        candidates = themes_module.words_for_theme(theme)
        if candidates:
            return _word_payload(random.choice(candidates), language)
        # Unknown/empty theme -- degrade to fully random rather than 404,
        # same approach kid_progress.py takes for a missing VaakMirrorSession.

    chosen = random.choice(list(index.keys()))
    return _word_payload(chosen, language)


@router.get("/characters")
def characters(patient_id: str = Depends(get_current_patient_id)):
    return {"characters": get_characters()}


@router.get("/mastery")
async def get_mastery(
    patient_id: str = Depends(get_current_patient_id),
    db: AsyncSession = Depends(get_db),
):
    """Per-phoneme accuracy for the logged-in kid. Same data is available
    in-process (no HTTP needed) to other games/agent logic via
    mastery.get_mastery_summary()/get_weak_phonemes()."""
    summary = await mastery.get_mastery_summary(db, uuid.UUID(patient_id))
    weak = await mastery.get_weak_phonemes(db, uuid.UUID(patient_id))
    return {"phonemes": summary, "weakest": weak}


@router.post("/speak")
async def speak_endpoint(
    text: str = Form(...),
    character: str = Form(default="BOLT"),
    patient_id: str = Depends(get_current_patient_id),
):
    audio_bytes = tts_speak(text, character)
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post("/image")
async def image_endpoint(
    phrase: str = Form(...),
    patient_id: str = Depends(get_current_patient_id),
):
    result = get_image_for_phrase(phrase)
    if not result["found"]:
        return {"found": False, "phrase": phrase}
    return Response(
        content=result["image_bytes"],
        media_type="image/png",
        headers={
            "X-Matched-Word": result["matched_word"],
            "X-Match-Type": result["match_type"],
            "X-Confidence": str(result["confidence"]),
        },
    )


@router.post("/evaluate")
async def evaluate(
    audio: UploadFile = File(...),
    target_word: str = Form(...),
    language: str = Form(default="english"),
    condition: str = Form(default="autism"),
    attempt_number: int = Form(default=1),
    session_id: str = Form(default=None),
    character: str = Form(default="BOLT"),
    theme: str = Form(default=None),
    patient_id: str = Depends(get_current_patient_id),
    db: AsyncSession = Depends(get_db),
):
    session_id = session_id or str(uuid.uuid4())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        from app.main import whisper  # reuses the whisper instance agenti_ai's assessment already loads
        segments, _ = whisper.transcribe(tmp_path)
        transcript = " ".join([s.text.strip() for s in segments]).strip().lower()
        target_phonemes = get_phonemes(target_word, language)
        detected_phonemes = get_phonemes(transcript, language) if transcript else []
        acoustic_raw = analyse_audio(tmp_path, transcript)
        result = build_attempt_result(
            session_id=session_id,
            child_id=patient_id,
            target_word=target_word,
            target_phonemes=target_phonemes,
            transcript=transcript,
            detected_phonemes=detected_phonemes,
            acoustic_raw=acoustic_raw,
            attempt_number=attempt_number,
            condition=condition,
            character=character,
        )

        # Persist for mastery tracking. Isolated in its own try/except --
        # a DB hiccup here must never cost the kid their already-computed
        # result, which is why this runs after `result` exists rather than
        # being folded into build_attempt_result.
        try:
            await mastery.record_attempt(db, uuid.UUID(patient_id), result, theme_id=theme)
        except Exception as e:
            print(f"mastery.record_attempt failed (non-fatal): {e}")

        return result
    finally:
        os.unlink(tmp_path)
