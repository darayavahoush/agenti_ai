from numba.core.types import Optional
import os
import uuid
import tempfile
from typing import Tuple, List
import numpy as np
import librosa
import torch
from fastapi import UploadFile
from pydub import AudioSegment
from silero_vad import get_speech_timestamps, load_silero_vad
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# LOAD MODELS
# ---------------------------------------------------
try:
    vad_model = load_silero_vad()
    logger.info("✅ Silero VAD loaded")
except Exception as e:
    vad_model = None
    logger.error(f"❌ VAD error: {e}")


# ---------------------------------------------------
# SAVE AUDIO
# ---------------------------------------------------
def save_audio(file: UploadFile) -> str:
    logger.info(f"📁 Filename: {file.filename}")
    logger.info(f"📋 Content-Type: {file.content_type}")
    logger.info(f"📊 File size: {file.file.getbuffer().nbytes if hasattr(file.file, 'getbuffer') else 'unknown'}")

    # The browser's MediaRecorder actually records WebM/Opus (Chrome/Edge)
    # or MP4/AAC (Safari) no matter what filename/content-type the frontend
    # blob claims -- it's just labeled "recording.wav" / "audio/wav" without
    # any real re-encoding. Trusting that label made save_audio write raw
    # WebM/AAC bytes to a .wav path, which Parselmouth/libsndfile then
    # rejected with "Format not recognised". So: always decode with pydub
    # (via ffmpeg, which auto-detects the real container/codec from the
    # bytes) and re-encode to genuine 16-bit PCM WAV, ignoring the claimed
    # extension entirely.
    raw_bytes = file.file.read()

    tmp_in_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.upload")
    with open(tmp_in_path, "wb") as f:
        f.write(raw_bytes)

    path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
    try:
        audio = AudioSegment.from_file(tmp_in_path)  # ffmpeg sniffs real format
        audio.export(path, format="wav")
    except Exception as e:
        logger.error(f"❌ Transcode error: {e}")
        raise
    finally:
        if os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)

    logger.info(f"💾 Saved as: {path}")
    logger.info(f"📏 Saved file size: {os.path.getsize(path)} bytes")
    return path


# ---------------------------------------------------
# LOAD AUDIO
# ---------------------------------------------------
def load_audio(
    path: str,
    sr: int = 16000
) -> Tuple[np.ndarray, int]:
    logger.info(f"🔊 Loading audio from: {path} with sample rate: {sr}")
    y, loaded_sr = librosa.load(path, sr=sr)
    logger.info(f"📊 Loaded audio shape: {y.shape} actual sample rate: {loaded_sr}")
    return y, loaded_sr


# ---------------------------------------------------
# NORMALIZE AUDIO
# ---------------------------------------------------
def normalize_audio(y: np.ndarray) -> np.ndarray:
    return librosa.util.normalize(y)


# ---------------------------------------------------
# TRIM SILENCE
# ---------------------------------------------------
def trim_audio(y: np.ndarray, top_db: int = 10) -> np.ndarray:
    y_trimmed, _ = librosa.effects.trim(y, top_db=top_db)
    return y_trimmed


# ---------------------------------------------------
# VAD SPLIT (Silero)
# ---------------------------------------------------
def vad_split(y: np.ndarray, sr: int) -> List[np.ndarray]:
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
def select_child_segment(y: np.ndarray, sr: int) -> np.ndarray:
    segments = vad_split(y, sr)

    from typing import Optional

    best_audio: Optional[np.ndarray] = None
    best_score = -999

    for audio in segments:
        if len(audio) < 1600:
            continue

        # energy
        energy = np.mean(librosa.feature.rms(y=audio))

        # pitch
        pitches, _ = librosa.piptrack(y=audio, sr=sr)
        pitch_vals = pitches[pitches > 0]
        pitch = np.mean(pitch_vals) if len(pitch_vals) else 0

        duration = len(audio) / sr

        # 🎯 CHILD HEURISTIC
        # Prefer strong, voiced segments and avoid tiny noise bursts.
        score = (energy * 100) + (pitch * 0.35) - (duration * 0.5)

        if score > best_score:
            best_score = score
            best_audio = audio

    if best_audio is None:
        return y

    logger.info(f"🎯 Selected segment score: {best_score:.2f}")
    return best_audio


# ---------------------------------------------------
# AUDIO FEATURES
# ---------------------------------------------------
def extract_features(y: np.ndarray, sr: int) -> dict[str, float]:
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
# DELETE AUDIO
# ---------------------------------------------------
def delete_audio(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logger.info(f"Failed to delete {path}: {e}")
