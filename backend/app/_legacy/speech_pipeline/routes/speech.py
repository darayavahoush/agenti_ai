import os

import soundfile as sf
from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel

from app.tools.audio_tool import (
    save_audio,
    load_audio,
    normalize_audio,
    trim_audio,
    select_child_segment,
    delete_audio
)
from app.tools.speech_tool import transcribe
from app.tools.phoneme_tool import get_basic_phonemes
from app.tools.multilang_phoneme_tool import get_basic_phonemes_multilang
from app._legacy.speech_pipeline.graph.speech_graph import speech_graph
from app.state.speech_state import SpeechState

router = APIRouter(prefix="/speech", tags=["Speech Therapy"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()















@router.post("/therapy")
async def therapy(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    target_word: str = Form(...),
    therapy_mode: str = Form(...),
    language: str = Form(default="en"),
    db: Session = Depends(get_db)
):
    try:

        # -------------------
        # SAVE AUDIO
        # -------------------
        path = save_audio(file)

        try:
            try:
                info = sf.info(path)
                print("AUDIO INFO:", info)
            except Exception as e:
                print("SOUNDFILE ERROR:", e)

            # Construct input state for LangGraph workflow
            initial_state = SpeechState(
                patient_name=patient_name,
                target_word=target_word,
                therapy_mode=therapy_mode,
                language=language,
                audio_path=path,
                sample_rate=None,
                audio=None,
                child_audio=None,
                transcript=None,
                spoken_word=None,
                expected_phonemes=[],
                spoken_phonemes=[],
                phoneme_accuracy=None,
                phoneme_matches=[],
                duration=None,
                pitch=None,
                loudness=None,
                accuracy=None,
                feedback=None,
                stars=None,
                expected_phonemes_display=[],
                spoken_phonemes_display=[],
                reasoning=None,
                recommendations=[],
                therapist_observations=None,
                suggested_exercises=[],
                repeat_word=None,
                progress_report=None,
                difficulty_adjustment=None,
                next_word=None,
                next_exercise=None,
                session_difficulty=None,
                intensive_practice_triggered=None,
                intensive_practice_message=None,
                error=None
            )

            # Invoke LangGraph orchestrating SpeechAnalysisAgent
            result_state = speech_graph.invoke(initial_state)

            if result_state.get("error"):
                raise Exception(result_state["error"])

            # -------------------
            # SAVE SESSION TO DB
            # -------------------
            clean_patient_name = patient_name.strip()
            patient = db.query(Patient).filter(
                Patient.name.ilike(clean_patient_name)
            ).first()

            if patient is None:
                patient = Patient(
                    name=clean_patient_name,
                    age=None,
                    language=None
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

            session_record = SessionModel(
                patient_id=patient.id,
                target_word=target_word,
                spoken_word=result_state["spoken_word"] if result_state["spoken_word"] else "No speech detected",
                accuracy=int(round(result_state["accuracy"] or 0)),
                feedback=result_state["feedback"],
                stars=result_state["stars"],
                session_type="word_practice",
                pitch=result_state["pitch"],
                duration=result_state["duration"],
                loudness=result_state["loudness"]
            )
            db.add(session_record)
            db.commit()
            db.refresh(session_record)

            # -------------------
            # RESPONSE
            # -------------------
            return {
                "child_name": patient_name,
                "patient_id": str(patient.id),
                "session_id": str(session_record.id),
                "target_word": target_word,
                "spoken_word": (
                    result_state["spoken_word"]
                    if result_state["spoken_word"]
                    else "No speech detected"
                ),
                "full_transcript": result_state["transcript"],
                "accuracy": result_state["accuracy"],
                "phoneme_accuracy": result_state["phoneme_accuracy"],
                "phoneme_matches": result_state["phoneme_matches"],
                "expected_phonemes": result_state["expected_phonemes"],
                "spoken_phonemes": result_state["spoken_phonemes"],
                "expected_phonemes_display": result_state["expected_phonemes_display"],
                "spoken_phonemes_display": result_state["spoken_phonemes_display"],
                "duration": result_state["duration"],
                "loudness": result_state["loudness"],
                "pitch": result_state["pitch"],
                "feedback": result_state["feedback"],
                "stars": result_state["stars"],
                # Multi-Agent Outputs
                "therapist_observations": result_state.get("therapist_observations"),
                "suggested_exercises": result_state.get("suggested_exercises", []),
                "repeat_word": result_state.get("repeat_word"),
                "progress_report": result_state.get("progress_report"),
                "difficulty_adjustment": result_state.get("difficulty_adjustment"),
                "next_word": result_state.get("next_word"),
                "next_exercise": result_state.get("next_exercise"),
                "session_difficulty": result_state.get("session_difficulty"),
                "intensive_practice_triggered": result_state.get("intensive_practice_triggered"),
                "intensive_practice_message": result_state.get("intensive_practice_message"),
                "reasoning": result_state.get("reasoning"),
                "recommendations": result_state.get("recommendations", [])
            }
        finally:
            # Cleanup audio file
            delete_audio(path)

    except Exception as e:

        print("THERAPY ERROR:", e)

        return {
            "error": str(e)
        }
    
@router.post("/phonemes/preview")
async def preview_phonemes(
    word: str = Form(...)
):

    return {
        "success": True,
        "data": {
            "phonemes": get_basic_phonemes(word)
        }
    }
    
@router.post("/phonemes")
async def get_phonemes(
    word: str = Form(...)
):

    return {
        "success": True,
        "data": {
            "word": word,
            "phonemes": get_basic_phonemes(word)
        }
    }

    phonemes = get_basic_phonemes(word)

    return {
        "word": word,
        "phonemes": phonemes
    }

@router.post("/compare")
async def compare_word(
    file: UploadFile = File(...),
    target_word: str = Form(...)
):

    result = await therapy(
        file=file,
        patient_name="Demo",
        target_word=target_word,
        therapy_mode="Full Word Match"
    )

    return {
        "success": True,
        "data": {
            "target_word": result["target_word"],
            "transcript": result["spoken_word"],
            "accuracy": result["accuracy"],
            "feedback": result["feedback"],
            "expected_phonemes": result["expected_phonemes"],
            "spoken_phonemes": result["spoken_phonemes"],
            "matches": result["phoneme_matches"]
        }
    }

@router.post("/compare_phoneme")
@router.post("/compare-phoneme")
async def compare_phoneme(
    file: UploadFile = File(...),
    target_phoneme: str = Form(...),
    language: str = Form(default="en")
):
    try:

        # Save audio
        path = save_audio(file)

        # Load audio
        y, sr = load_audio(path)

        y = normalize_audio(y)

        y = trim_audio(y, top_db=10)

        # Use same child-segment logic
        y_child = select_child_segment(y, sr)
        if y_child is None or len(y_child) < 300:
            y_child = y

        # Transcribe with language support so native script can be returned
        spoken_word = transcribe(
            y_child,
            sr,
            language=language
        )

        if not spoken_word:
            spoken_word = transcribe(
                y,
                sr,
                language=language
            )

        # Convert transcript → phonemes using multilingual helpers
        spoken_phonemes = get_basic_phonemes_multilang(
            spoken_word,
            language
        )

        correct = target_phoneme in spoken_phonemes

        # cleanup
        delete_audio(path)

        return {
            "success": True,
            "data": {
                "correct": correct,
                "transcript": spoken_word,
                "detected_phonemes": spoken_phonemes,
                "feedback": (
                    "Great Job!"
                    if correct
                    else f"Try emphasizing /{target_phoneme}/"
                )
            }
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }