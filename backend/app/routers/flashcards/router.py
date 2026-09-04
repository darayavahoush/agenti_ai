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
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.vaakmirror_auth import get_current_patient_id
from app.database import get_db

from .tts import speak as tts_speak, get_characters
from app.services.image.matcher import get_image_for_phrase
from .processor import analyse_audio
from .scorer import build_attempt_result
from .grapheme_to_phoneme import get_phonemes
from . import themes as themes_module
from . import mastery
from app.services.phoneme.svg import get_phoneme_card
from app.services.phoneme.drill import get_acoustic_feedback
import logging

logger = logging.getLogger(__name__)


_DATA_DIR = Path(__file__).resolve().parents[3] / 'data' / 'flashcard_images'
_INDEX_PATH = _DATA_DIR / 'index.json'

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


def _word_payload(word: str, language: str) -> dict:
    # Used to read raw bytes straight out of data/flashcard_images/index.json --
    # a small, hand-curated cache of old Wikimedia/OpenClipart scrapes, separate
    # from (and lower quality than) the ARASAAC-backed image service Assessment's
    # alphabet screen and VaakMirror already use. get_image_for_phrase gives real
    # pictogram matches (with a semantic-similarity fallback for anything not
    # pre-downloaded yet), same as everywhere else in the app -- this index.json
    # lookup here is now only for confirming `word` is a real flashcard word;
    # themes.py still owns the actual word list.
    with open(_INDEX_PATH) as f:
        index = json.load(f)
    if word not in index:
        raise KeyError(word)
    result = get_image_for_phrase(word)
    image_b64 = base64.b64encode(result["image_bytes"]).decode() if result.get("found") and result.get("image_bytes") else None
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


@router.get("/phoneme-card/{phoneme}")
def phoneme_card(phoneme: str):
    """
    Mouth-shape diagram + tip for a single ARPAbet phoneme, e.g. /flashcards/phoneme-card/SH.
    Same shape as speech-repeater's /phoneme-card/{phoneme} -- {ipa, name, example_word,
    tip, mouth_svg, common_errors, category} -- so the frontend result panel can fetch
    a card for each phoneme the kid got wrong and show how to fix it.
    """
    card = get_phoneme_card(phoneme.upper())
    if not card:
        raise HTTPException(status_code=404, detail=f"No phoneme data for '{phoneme}'")
    return card


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
    # Was entirely absent from this route -- the frontend's "Slow" button
    # already sent a speed value with no field here to receive it, so it
    # was silently dropped and every request rendered at the character's
    # default speed=1.0 regardless of which button was tapped.
    speed: float = Form(default=1.0),
    patient_id: str = Depends(get_current_patient_id),
):
    try:
        audio_bytes = tts_speak(text, character, speed=speed)
    except Exception as e:
        logger.error(f"speak_endpoint: TTS failed for text={text!r} character={character!r}: {e}")
        raise HTTPException(status_code=502, detail="Text-to-speech is temporarily unavailable")
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
        # NOTE: was `from app.main import whisper` -- app/main.py never
        # defines or imports anything named `whisper`, so this raised an
        # ImportError on every single call, outside any except clause that
        # could catch it -- a raw 500 on every recording, which is the
        # "error when analysing voice" in Flashcards. The actual shared
        # instance the comment refers to is `whisper_model` in
        # app/tools/speech_tool.py (assessment's own transcribe() already
        # reuses it). It can be None if the model failed to load at startup
        # (speech_tool.py logs and continues rather than crashing the app),
        # so that's handled explicitly instead of segfaulting on
        # None.transcribe(...).
        from app.tools.speech_tool import whisper_model
        if whisper_model is None:
            logger.error("/flashcards/evaluate: whisper_model unavailable (failed to load at startup)")
            raise HTTPException(status_code=503, detail="Voice checking is temporarily unavailable — try again in a moment.")
        segments, _ = whisper_model.transcribe(tmp_path)
        transcript = " ".join([s.text.strip() for s in segments]).strip().lower()
        target_phonemes = get_phonemes(target_word, language)
        detected_phonemes = get_phonemes(transcript, language) if transcript else []
        try:
            acoustic_raw = analyse_audio(tmp_path, transcript)
        except RuntimeError as e:
            # load_and_clean() raises this for a broken/empty conversion (bad
            # upload, unsupported codec, ffmpeg missing) -- logged in full so
            # the actual cause shows up in server logs, but the kid just sees
            # a clean "try recording again" rather than a raw 500.
            logger.error(f"/flashcards/evaluate: audio processing failed for patient={patient_id}: {e}")
            raise HTTPException(status_code=422, detail="We couldn't hear that clearly — try recording again.")
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
            logger.info(f"mastery.record_attempt failed (non-fatal): {e}")

        # Bonus feedback only -- doesn't touch result.repeat_needed/composite_score,
        # which still drive pass/fail exactly as before. acoustic_tips are general
        # voice-quality tips (loudness/pitch/rate); the frontend fetches per-phoneme
        # mouth-diagram cards separately via GET /phoneme-card/{phoneme} for whichever
        # phonemes in result.phoneme_scores.matches came back incorrect.
        try:
            acoustic_tips = get_acoustic_feedback(acoustic_raw, condition)
        except Exception as e:
            logger.info(f"get_acoustic_feedback failed (non-fatal): {e}")
            acoustic_tips = []

        result_dict = result.model_dump()
        result_dict["acoustic_tips"] = acoustic_tips
        return result_dict
    finally:
        os.unlink(tmp_path)
