import numpy as np
import parselmouth
from parselmouth.praat import call
import librosa
import soundfile as sf
import noisereduce as nr
import tempfile
import os
from app.core.config import settings


def load_and_clean(audio_path: str):
    import subprocess, tempfile
    # Convert to wav first (handles webm from browser)
    tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    tmp_wav.close()
    subprocess.run(['ffmpeg', '-y', '-i', audio_path, '-ar', '16000', '-ac', '1', tmp_wav.name],
                   capture_output=True)
    y, sr = librosa.load(tmp_wav.name, sr=16000, mono=True)
    os.unlink(tmp_wav.name)
    y_clean = nr.reduce_noise(y=y, sr=sr, stationary=False)
    return y_clean, sr


def save_temp(y, sr: int) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, y, sr)
    return tmp.name


def measure_loudness(y, sr: int) -> dict:
    rms = float(np.sqrt(np.mean(y ** 2)))
    db = float(20 * np.log10(rms + 1e-9))
    in_range = settings.TARGET_RMS_MIN <= rms <= settings.TARGET_RMS_MAX
    if in_range:
        score = 100.0
    elif rms < settings.TARGET_RMS_MIN:
        score = (rms / settings.TARGET_RMS_MIN) * 100
    else:
        score = max(0.0, 100 - ((rms - settings.TARGET_RMS_MAX) / settings.TARGET_RMS_MAX) * 100)
    return {"loudness_rms": rms, "loudness_db": db, "loudness_in_range": in_range, "loudness_score": round(score, 2)}


def measure_pitch(wav_path: str) -> dict:
    snd = parselmouth.Sound(wav_path)
    pitch = call(snd, "To Pitch", 0.0, 75, 500)
    pitch_values = pitch.selected_array["frequency"]
    pitch_values = pitch_values[pitch_values > 0]
    if len(pitch_values) == 0:
        return {"pitch_mean_hz": 0.0, "pitch_std_hz": 0.0, "pitch_variation": "undetected", "pitch_score": 50.0}
    mean = float(np.mean(pitch_values))
    std = float(np.std(pitch_values))
    if std < 10:
        variation, score = "flat", 75.0
    elif std < 30:
        variation, score = "normal", 100.0
    elif std < 60:
        variation, score = "expressive", 85.0
    else:
        variation, score = "erratic", 60.0
    return {"pitch_mean_hz": round(mean, 2), "pitch_std_hz": round(std, 2), "pitch_variation": variation, "pitch_score": score}


def measure_voice_quality(wav_path: str) -> dict:
    snd = parselmouth.Sound(wav_path)
    point_process = call(snd, "To PointProcess (periodic, cc)", 75, 500)
    jitter = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3) * 100
    shimmer = call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6) * 100
    harmonicity = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
    hnr = call(harmonicity, "Get mean", 0, 0)
    jitter_score = 100.0 if jitter < 1.0 else max(0.0, 100 - (jitter - 1.0) * 30)
    shimmer_score = 100.0 if shimmer < 3.0 else max(0.0, 100 - (shimmer - 3.0) * 15)
    hnr_score = min(100.0, (max(hnr, 0) / 25) * 100)
    voice_quality_score = (jitter_score + shimmer_score + hnr_score) / 3
    return {"jitter_percent": round(jitter, 3), "shimmer_percent": round(shimmer, 3), "hnr_db": round(hnr, 2), "voice_quality_score": round(voice_quality_score, 2)}


def measure_formants(wav_path: str) -> dict:
    try:
        snd = parselmouth.Sound(wav_path)
        formants = call(snd, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
        f1 = call(formants, "Get mean", 1, 0, 0, "Hertz")
        f2 = call(formants, "Get mean", 2, 0, 0, "Hertz")
        return {"f1_hz": round(f1, 2), "f2_hz": round(f2, 2)}
    except Exception:
        return {"f1_hz": None, "f2_hz": None}


def count_syllables(word: str) -> int:
    word = word.lower().strip()
    count, prev_vowel = 0, False
    for char in word:
        is_vowel = char in "aeiouy"
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    return max(1, count)


def measure_speaking_rate(transcript: str, duration_sec: float) -> dict:
    syllable_count = sum(count_syllables(w) for w in transcript.split())
    rate = syllable_count / max(duration_sec, 0.1)
    if settings.TARGET_RATE_MIN <= rate <= settings.TARGET_RATE_MAX:
        rating, score = "normal", 100.0
    elif rate < settings.TARGET_RATE_MIN:
        rating, score = "slow", (rate / settings.TARGET_RATE_MIN) * 100
    else:
        rating, score = "fast", max(60.0, 100 - ((rate - settings.TARGET_RATE_MAX) / settings.TARGET_RATE_MAX) * 50)
    return {"speaking_rate": round(rate, 2), "speaking_rate_rating": rating, "rate_score": round(score, 2)}


def analyse_audio(audio_path: str, transcript: str) -> dict:
    y, sr = load_and_clean(audio_path)
    clean_path = save_temp(y, sr)
    duration = len(y) / sr
    try:
        loudness = measure_loudness(y, sr)
        pitch = measure_pitch(clean_path)
        voice_quality = measure_voice_quality(clean_path)
        formants = measure_formants(clean_path)
        rate = measure_speaking_rate(transcript, duration)
        return {**loudness, **pitch, **voice_quality, **formants, **rate}
    finally:
        os.unlink(clean_path)
