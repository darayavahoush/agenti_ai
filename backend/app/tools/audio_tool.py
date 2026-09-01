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

    # NOTE: this used to score every VAD-detected segment and keep only the
    # single highest-scoring one, discarding the rest outright. The score
    # formula (energy*100 + pitch*0.35 - duration*0.5) is almost entirely
    # driven by average energy -- duration barely moves it -- so a short,
    # loud transient (a mic click/pop at the start of the recording, a
    # cough, a tap sound) reliably outscored the child's actual (quieter,
    # longer) word. Whenever VAD also happened to split one continuous
    # word into two chunks around a natural micro-pause, keeping only the
    # "best" chunk meant transcribing a fragment of the word instead of
    # the whole thing -- e.g. only catching "eigh-" or a stray "uh" for a
    # child who clearly said "eight", which is exactly the truncated,
    # nonsensical single-phoneme detections being reported.
    #
    # Fix: keep every VAD segment that's long enough to plausibly be
    # speech (the existing 1600-sample / 0.1s floor) and concatenate them
    # in order, so the full utterance survives instead of only its
    # loudest fragment. VAD's job is already to strip silence/noise gaps
    # between speech; this just stops us from throwing away real speech
    # segments it correctly found.
    valid_segments = [audio for audio in segments if len(audio) >= 1600]

    if not valid_segments:
        return y

    if len(valid_segments) == 1:
        return valid_segments[0]

    logger.info(f"🎯 Merging {len(valid_segments)} detected speech segments into one utterance")
    return np.concatenate(valid_segments)


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
