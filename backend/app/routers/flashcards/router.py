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

from app.vaakmirror_auth import get_current_patient_id

from .tts import speak as tts_speak, get_characters
from .matcher import get_image_for_phrase
from .processor import analyse_audio
from .scorer import build_attempt_result
from .grapheme_to_phoneme import get_phonemes

_DATA_DIR = Path(__file__).resolve().parents[3] / 'data' / 'flashcard_images'
_INDEX_PATH = _DATA_DIR / 'index.json'

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


@router.get("/random-word")
def random_word(language: str = "english", patient_id: str = Depends(get_current_patient_id)):
    with open(_INDEX_PATH) as f:
        index = json.load(f)
    word = random.choice(list(index.keys()))
    image_path = _DATA_DIR / index[word]
    image_b64 = base64.b64encode(image_path.read_bytes()).decode() if image_path.exists() else None
    return {
        "word": word,
        "language": language,
        "phonemes": get_phonemes(word, language),
        "image_base64": image_b64,
    }


@router.get("/characters")
def characters(patient_id: str = Depends(get_current_patient_id)):
    return {"characters": get_characters()}


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
    patient_id: str = Depends(get_current_patient_id),
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
        return result
    finally:
        os.unlink(tmp_path)
