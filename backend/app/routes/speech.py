import os
import uuid
import tempfile
import re

import numpy as np
import librosa
import soundfile as sf
import whisper
import torch

from fastapi import APIRouter, UploadFile, File, Form
from rapidfuzz import fuzz
from silero_vad import get_speech_timestamps, load_silero_vad

router = APIRouter(prefix="/speech", tags=["Speech Therapy"])

# ---------------------------------------------------
# LOAD MODELS
# ---------------------------------------------------
try:
    whisper_model = whisper.load_model("base.en")
    print("✅ Whisper loaded")
except Exception as e:
    whisper_model = None
    print("❌ Whisper error:", e)

try:
    vad_model = load_silero_vad()
    print("✅ Silero VAD loaded")
except Exception as e:
    vad_model = None
    print("❌ VAD error:", e)


# ---------------------------------------------------
# SAVE AUDIO
# ---------------------------------------------------
def save_audio(file: UploadFile):
    path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


# ---------------------------------------------------
# NORMALIZE TEXT
# ---------------------------------------------------
def normalize_text(text):
    return re.sub(r'[^a-z ]', '', text.lower()).strip()


# ---------------------------------------------------
# VAD SPLIT (Silero)
# ---------------------------------------------------
def vad_split(y, sr):
    if vad_model is None:
        return [y]

    y_tensor = torch.tensor(y)

    timestamps = get_speech_timestamps(
        y_tensor,
        vad_model,
        sampling_rate=sr
    )

    segments = []

    for seg in timestamps:
        start = seg["start"]
        end = seg["end"]
        segments.append(y[start:end])

    return segments if segments else [y]


# ---------------------------------------------------
# SMART CHILD SEGMENT SELECTION
# ---------------------------------------------------
def select_child_segment(y, sr):

    segments = vad_split(y, sr)

    best_audio = None
    best_score = -999

    for audio in segments:

        if len(audio) < 500:
            continue

        # energy
        energy = np.mean(librosa.feature.rms(y=audio))

        # pitch
        pitches, _ = librosa.piptrack(y=audio, sr=sr)
        pitch_vals = pitches[pitches > 0]
        pitch = np.mean(pitch_vals) if len(pitch_vals) else 0

        duration = len(audio) / sr

        # 🎯 CHILD HEURISTIC
        score = (pitch * 0.6) - (energy * 100) - (duration * 2)

        if score > best_score:
            best_score = score
            best_audio = audio

    if best_audio is None:
        return y

    print(f"🎯 Selected segment score: {best_score:.2f}")

    return best_audio


# ---------------------------------------------------
# TRANSCRIPTION
# ---------------------------------------------------
def transcribe(y, sr):
    if whisper_model is None:
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        sf.write(tmp_path, y, sr)
        result = whisper_model.transcribe(tmp_path)
        return normalize_text(result["text"])
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ---------------------------------------------------
# BEST WORD MATCH
# ---------------------------------------------------
def extract_spoken_part(transcript, target):

    words = transcript.split()
    if not words:
        return ""

    target = target.lower()

    best_match = ""
    best_score = 0

    for word in words:
        # Compare progressively smaller prefixes
        for i in range(1, len(word) + 1):
            part = word[:i]

            score = fuzz.ratio(part, target[:len(part)])

            if score > best_score:
                best_score = score
                best_match = part

    # 🔥 HARD RULE: do NOT exceed target length
    if len(best_match) > len(target):
        best_match = best_match[:len(target)]

    return best_match
# ---------------------------------------------------
# SCORE
# ---------------------------------------------------
def compute_score(target, spoken):

    if spoken == "":
        return 0

    target = target.lower()
    spoken = spoken.lower()

    # Base similarity
    similarity = fuzz.ratio(target, spoken)

    # Length penalty (VERY IMPORTANT)
    length_ratio = len(spoken) / len(target)

    # Penalize short pronunciations
    if length_ratio < 0.5:
        return int(similarity * length_ratio)

    # Medium partial
    if length_ratio < 0.8:
        return int(similarity * 0.8)

    # Full word attempt
    return int(similarity)


# ---------------------------------------------------
# FEEDBACK
# ---------------------------------------------------
def generate_feedback(score, target, spoken):
    if spoken == "":
        return "No speech detected. Try again slowly.", 1

    if score >= 90:
        return "Excellent pronunciation! 🎉", 5

    if score >= 70:
        return f"Very good! Improve ending of '{target}'.", 4

    if score >= 50:
        return f"You said '{spoken}'. Try full word '{target}'.", 3

    return f"Break it: {target[:2]}...{target}", 2


# ---------------------------------------------------
# AUDIO FEATURES
# ---------------------------------------------------
def extract_features(y, sr):
    y = librosa.util.normalize(y)
    y, _ = librosa.effects.trim(y)

    duration = librosa.get_duration(y=y, sr=sr)
    loudness = float(np.mean(librosa.feature.rms(y=y)))

    pitches, _ = librosa.piptrack(y=y, sr=sr)
    pitch_vals = pitches[pitches > 0]
    pitch = float(np.mean(pitch_vals)) if len(pitch_vals) else 0

    return {
        "duration": round(duration, 2),
        "loudness": round(loudness, 4),
        "pitch": round(pitch, 2)
    }


# ---------------------------------------------------
# MAIN API
# ---------------------------------------------------
@router.post("/therapy")
async def therapy(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    target_word: str = Form(...)
):
    try:
        path = save_audio(file)

        y, sr = librosa.load(path, sr=16000)

        # 🎯 Lightweight child selection
        y_child = select_child_segment(y, sr)

        # fallback safety
        if y_child is None or len(y_child) < 1000:
            y_child = y

        # -------------------
        # ANALYSIS
        # -------------------
        transcript = transcribe(y_child, sr)

        target = normalize_text(target_word)
        spoken = extract_spoken_part(transcript, target)
        spoken = normalize_text(spoken)
        score = compute_score(target, spoken)
        feedback, stars = generate_feedback(score, target, spoken)

        metrics = extract_features(y_child, sr)

        os.remove(path)

        return {
            "child_name": patient_name,
            "target_word": target_word,
            "spoken_word": spoken if spoken else "No speech detected",
            "full_transcript": transcript,
            "accuracy": score,
            "duration": metrics["duration"],
            "loudness": metrics["loudness"],
            "pitch": metrics["pitch"],
            "feedback": feedback,
            "stars": stars
        }

    except Exception as e:
        return {"error": str(e)}