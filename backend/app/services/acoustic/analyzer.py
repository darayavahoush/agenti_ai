import numpy as np
import librosa


# ---------------------------------------------------
# DEFAULT THRESHOLDS
# ---------------------------------------------------

TARGET_RMS_MIN = 0.03
TARGET_RMS_MAX = 0.30

TARGET_RATE_MIN = 2.0
TARGET_RATE_MAX = 5.0


# ---------------------------------------------------
# LOUDNESS
# ---------------------------------------------------

def measure_loudness(y, sr):

    rms = float(
        np.sqrt(
            np.mean(y ** 2)
        )
    )

    db = float(
        20 * np.log10(
            rms + 1e-9
        )
    )

    in_range = (
        TARGET_RMS_MIN
        <= rms
        <= TARGET_RMS_MAX
    )

    if in_range:

        score = 100.0

    elif rms < TARGET_RMS_MIN:

        score = (
            rms /
            TARGET_RMS_MIN
        ) * 100

    else:

        score = max(
            0.0,
            100 -
            (
                (
                    rms -
                    TARGET_RMS_MAX
                )
                /
                TARGET_RMS_MAX
            ) * 100
        )

    return {

        "loudness_rms": round(rms, 4),

        "loudness_db": round(db, 2),

        "loudness_in_range": in_range,

        "loudness_score": round(
            score,
            2
        )
    }


# ---------------------------------------------------
# PITCH
# ---------------------------------------------------

def measure_pitch(y, sr):

    pitches, _ = librosa.piptrack(
        y=y,
        sr=sr
    )

    pitch_values = pitches[
        pitches > 0
    ]

    if len(pitch_values) == 0:

        return {

            "pitch_mean_hz": 0.0,

            "pitch_std_hz": 0.0,

            "pitch_variation": "undetected",

            "pitch_score": 50.0
        }

    mean = float(
        np.mean(
            pitch_values
        )
    )

    std = float(
        np.std(
            pitch_values
        )
    )

    if std < 10:

        variation = "flat"
        score = 75.0

    elif std < 30:

        variation = "normal"
        score = 100.0

    elif std < 60:

        variation = "expressive"
        score = 85.0

    else:

        variation = "erratic"
        score = 60.0

    return {

        "pitch_mean_hz": round(
            mean,
            2
        ),

        "pitch_std_hz": round(
            std,
            2
        ),

        "pitch_variation": variation,

        "pitch_score": score
    }


# ---------------------------------------------------
# SYLLABLE COUNT
# ---------------------------------------------------

def count_syllables(word):

    word = word.lower().strip()

    count = 0
    prev_vowel = False

    for char in word:

        is_vowel = (
            char in "aeiouy"
        )

        if (
            is_vowel
            and not prev_vowel
        ):
            count += 1

        prev_vowel = is_vowel

    return max(
        1,
        count
    )


# ---------------------------------------------------
# SPEAKING RATE
# ---------------------------------------------------

def measure_speaking_rate(
    transcript,
    duration_sec
):

    syllable_count = sum(
        count_syllables(word)
        for word in transcript.split()
    )

    rate = (
        syllable_count
        /
        max(
            duration_sec,
            0.1
        )
    )

    if (
        TARGET_RATE_MIN
        <= rate
        <= TARGET_RATE_MAX
    ):

        rating = "normal"
        score = 100.0

    elif rate < TARGET_RATE_MIN:

        rating = "slow"

        score = (
            rate
            /
            TARGET_RATE_MIN
        ) * 100

    else:

        rating = "fast"

        score = max(
            60.0,
            100 -
            (
                (
                    rate -
                    TARGET_RATE_MAX
                )
                /
                TARGET_RATE_MAX
            ) * 50
        )

    return {

        "speaking_rate": round(
            rate,
            2
        ),

        "speaking_rate_rating": rating,

        "rate_score": round(
            score,
            2
        )
    }


# ---------------------------------------------------
# MAIN ANALYZER
# ---------------------------------------------------

def analyze_acoustics(
    y,
    sr,
    transcript
):

    duration = (
        len(y)
        /
        sr
    )

    loudness = measure_loudness(
        y,
        sr
    )

    pitch = measure_pitch(
        y,
        sr
    )

    rate = measure_speaking_rate(
        transcript,
        duration
    )

    return {

        "duration": round(
            duration,
            2
        ),

        **loudness,

        **pitch,

        **rate
    }

