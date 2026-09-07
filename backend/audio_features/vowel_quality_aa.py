"""
aa level — vowel duration + jaw-openness/tongue-height, via formant tracking.

Drives Chime's own "Rocket Launch" mechanic: a held, open "aaa" powers a
rocket upward; losing the vowel quality or duration lets it fall back down.

Replaces vowel_loudness.py, which only measured RMS volume and never
checked whether the sound was actually an "aa" at all -- a loud shout of
any vowel (or non-vowel) scored the same as a correct one. "aa" (as in
"father") is a low, back/central vowel: jaw dropped, tongue low and
retracted, giving it the highest F1 of any vowel and a mid-range F2 --
the opposite corner of the vowel space from "oo" (low F1/F2) and "ee"
(low F1, high F2). It's also one of the easiest vowels to formant-track,
since a wide-open jaw gives a strong, distinctive F1 peak that's hard to
confuse with any other vowel -- there was no acoustic reason "aa" was
left on a cruder loudness-only check while oo/ee already got the real
treatment.

Same formant-tracking approach as vowel_quality.py/vowel_quality_ee.py --
needs the same ~200-500ms stable-voicing window, so buffer frames before
calling this rather than calling it per 50ms frame like the loudness-only
extractors.
"""

import numpy as np
import parselmouth
from .common import FeatureResult

# "aa" (as in "father") formant targets in Hz. Adult values run roughly
# F1=700-800, F2=1100-1200 (Peterson & Barney norms for /ɑ/) -- as with
# oo/ee, children's shorter vocal tracts push both formants meaningfully
# higher, so these are shifted up toward typical child-speech targets and
# given a tolerance band wide enough to absorb the spread across ages.
# Still a starting point pending recalibration against real child speech
# samples, not a substitute for it -- same caveat as the other two
# formant-based extractors in this module.
TARGET_F1 = 869.0  # calibrated from 3-rep real-mic recording, was 900.0
TARGET_F2 = 1546.0  # calibrated from 3-rep real-mic recording, was 1450.0
FORMANT_TOLERANCE_HZ = 400.0  # widest of the three vowels -- "aa" has the most open-jaw variability

MIN_VALID_DURATION_S = 0.15  # shorter than this, treat as not a real attempt


def extract(audio_chunk: np.ndarray, sample_rate: int = 16000) -> FeatureResult:
    duration_s = len(audio_chunk) / sample_rate
    if duration_s < MIN_VALID_DURATION_S:
        return FeatureResult(score=0.0, is_valid_attempt=False, raw_features={"duration_s": duration_s})

    sound = parselmouth.Sound(audio_chunk.astype(np.float64), sampling_frequency=sample_rate)
    formant = sound.to_formant_burg()

    # Sample formants across the middle 60% of the chunk (avoids onset/offset noise)
    start, end = duration_s * 0.2, duration_s * 0.8
    times = np.linspace(start, end, num=10)
    f1_vals, f2_vals = [], []
    for t in times:
        f1 = formant.get_value_at_time(1, t)
        f2 = formant.get_value_at_time(2, t)
        if f1 and f2 and not np.isnan(f1) and not np.isnan(f2):
            f1_vals.append(f1)
            f2_vals.append(f2)

    if not f1_vals:
        return FeatureResult(score=0.0, is_valid_attempt=False, raw_features={"duration_s": duration_s})

    mean_f1, mean_f2 = float(np.mean(f1_vals)), float(np.mean(f2_vals))
    f1_dist = abs(mean_f1 - TARGET_F1)
    f2_dist = abs(mean_f2 - TARGET_F2)
    quality_score = max(0.0, 1.0 - (f1_dist + f2_dist) / (2 * FORMANT_TOLERANCE_HZ))

    duration_score = min(1.0, duration_s / 1.5)  # 1.5s sustained "aa" = full score
    combined = float(quality_score * duration_score)

    return FeatureResult(
        score=combined,
        is_valid_attempt=True,
        raw_features={"f1": mean_f1, "f2": mean_f2, "duration_s": duration_s, "quality_score": quality_score},
    )
