from app.core.config import settings
from app.core.schema import PhonemeMatch, PhonemeScores, AcousticMetrics, AttemptResult
from typing import List, Tuple
import uuid
from datetime import datetime


def levenshtein(a: list, b: list) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i-1][j-1] if a[i-1] == b[j-1] else 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]


# Phoneme pairs that are acceptable substitutions in Indian English
INDIAN_ACCENT_EQUIVALENTS = {
    frozenset(["V", "W"]),       # Indian English merges v/w
    frozenset(["T", "RT"]),      # retroflex/dental t
    frozenset(["D", "RD"]),      # retroflex/dental d
    frozenset(["TH", "D"]),      # th→d is standard in Indian English
    frozenset(["TH", "T"]),      # th→t variant
    frozenset(["Z", "J"]),       # z→j common substitution
    frozenset(["AE", "EH"]),     # flat a vowel
    frozenset(["AO", "AH"]),     # o vowel merge
    frozenset(["IH", "IY"]),     # short/long i merge
    frozenset(["UW", "UH"]),     # oo vowel
    frozenset(["R", "RD"]),      # tapped r
}

def score_phonemes(expected: List[str], detected: List[str]) -> PhonemeScores:
    matches = []
    error_types = set()

    # Normalise case
    exp_upper = [p.upper() for p in expected]
    det_upper = [p.upper() for p in detected]

    for i, ep in enumerate(exp_upper):
        if i < len(det_upper):
            dp = det_upper[i]
            correct = ep == dp
            # Accept Indian accent equivalents as correct
            if not correct:
                pair = frozenset([ep, dp])
                if pair in INDIAN_ACCENT_EQUIVALENTS:
                    correct = True
                    error_types.add("indian_variant")
            # Partial credit: single-char near miss
            if not correct:
                if len(ep) == len(dp) == 1 and abs(ord(ep) - ord(dp)) <= 3:
                    error_types.add("near_miss")
                else:
                    error_types.add("substitution")
            matches.append(PhonemeMatch(expected=expected[i], detected=detected[i] if i < len(detected) else None, correct=correct))
        else:
            matches.append(PhonemeMatch(expected=expected[i], detected=None, correct=False))
            error_types.add("omission")

    if len(detected) > len(expected):
        error_types.add("addition")

    dist = levenshtein(exp_upper, det_upper)
    max_len = max(len(expected), len(detected), 1)

    # Base accuracy from edit distance
    base_accuracy = max(0.0, (1 - dist / max_len) * 100)

    # Bonus: if transcript word roughly matches target, boost by up to 10pts
    correct_count = sum(1 for m in matches if m.correct)
    total = max(len(expected), 1)
    precision = correct_count / total

    # Weighted blend: edit distance (70%) + precision (30%)
    accuracy = round(base_accuracy * 0.7 + precision * 100 * 0.3, 2)
    accuracy = min(100.0, accuracy)

    return PhonemeScores(
        matches=matches,
        accuracy=accuracy,
        error_types=list(error_types)
    )


def compute_composite(
    phoneme_accuracy: float,
    acoustic: dict,
    condition: str = "autism"
) -> float:
    weights = settings.WEIGHTS.get(condition, settings.WEIGHTS["autism"])

    composite = (
        phoneme_accuracy           * weights["phoneme"] +
        acoustic["loudness_score"] * weights["loudness"] +
        acoustic["pitch_score"]    * weights["pitch"] +
        acoustic["rate_score"]     * weights["rate"] +
        acoustic["voice_quality_score"] * weights["voice_quality"]
    )

    return round(composite, 2)


def should_repeat(composite_score: float, attempt_number: int) -> Tuple[bool, str]:
    if composite_score >= settings.SCORE_PASS:
        return False, "pass"
    elif composite_score >= settings.SCORE_RETRY and attempt_number < settings.MAX_ATTEMPTS:
        return True, "retry"
    elif composite_score >= settings.SCORE_SIMPLIFY:
        return True, "simplify"
    else:
        return True, "support"


FEEDBACK_RULES = {
    ("B", "W"): "Press both lips together firmly before starting the sound.",
    ("R", "W"): "Curl your tongue tip toward the roof of your mouth.",
    ("S", "TH"): "Keep your tongue behind your teeth, not between them.",
    ("K", "T"): "Let the back of your tongue touch the roof of your mouth.",
    ("L", "W"): "Place your tongue tip just behind your top feet.",
    ("G", "D"): "Start the sound from the back of your throat.",
    ("SH", "S"): "Round your lips and push air over your tongue.",
    ("CH", "SH"): "Touch the roof of your mouth then release the air.",
    ("TH", "D"): "Put your tongue gently between your teeth.",
    ("F", "P"): "Touch your top teeth to your bottom lip and blow air.",
    ("V", "B"): "Touch your top teeth to your bottom lip and use your voice.",
    ("Z", "S"): "Make the same shape as S but turn your voice on.",
}


def get_feedback(phoneme_scores: PhonemeScores) -> str:
    for match in phoneme_scores.matches:
        if not match.correct and match.detected:
            key = (match.expected.upper(), match.detected.upper())
            tip = FEEDBACK_RULES.get(key) or FEEDBACK_RULES.get((key[1], key[0]))
            if tip:
                return tip
    if phoneme_scores.accuracy < 50:
        return "Take a deep breath and try again slowly."
    return "Good try! Keep practising this sound."


def get_tiered_feedback(phoneme_scores: PhonemeScores, composite_score: float, attempt_number: int) -> dict:
    """Return feedback with severity tier for frontend to display differently."""
    tip = get_feedback(phoneme_scores)

    if composite_score >= 80:
        return {"tier": "pass", "title": "Amazing!", "tip": tip, "mood": "celebrate"}
    elif composite_score >= 65:
        return {"tier": "close", "title": "So close!", "tip": tip, "mood": "encourage"}
    elif composite_score >= 45:
        if attempt_number >= 2:
            return {"tier": "struggling", "title": "Let us slow it down", "tip": tip, "mood": "instruction"}
        return {"tier": "retry", "title": "Good try, once more!", "tip": tip, "mood": "encourage"}
    else:
        return {"tier": "support", "title": "Let us practise this sound first", "tip": tip, "mood": "instruction"}


def build_attempt_result(
    session_id: str,
    child_id: str,
    target_word: str,
    target_phonemes: List[str],
    transcript: str,
    detected_phonemes: List[str],
    acoustic_raw: dict,
    attempt_number: int,
    condition: str,
    character: str,
) -> AttemptResult:
    phoneme_scores = score_phonemes(target_phonemes, detected_phonemes)
    composite = compute_composite(phoneme_scores.accuracy, acoustic_raw, condition)
    repeat_needed, repeat_reason = should_repeat(composite, attempt_number)
    feedback_data = get_tiered_feedback(phoneme_scores, composite, attempt_number)
    feedback = feedback_data["tip"]

    acoustic = AcousticMetrics(
        loudness_rms=acoustic_raw["loudness_rms"],
        loudness_db=acoustic_raw["loudness_db"],
        loudness_in_range=acoustic_raw["loudness_in_range"],
        loudness_score=acoustic_raw["loudness_score"],
        pitch_mean_hz=acoustic_raw["pitch_mean_hz"],
        pitch_std_hz=acoustic_raw["pitch_std_hz"],
        pitch_variation=acoustic_raw["pitch_variation"],
        pitch_score=acoustic_raw["pitch_score"],
        speaking_rate=acoustic_raw["speaking_rate"],
        speaking_rate_rating=acoustic_raw["speaking_rate_rating"],
        rate_score=acoustic_raw["rate_score"],
        jitter_percent=acoustic_raw["jitter_percent"],
        shimmer_percent=acoustic_raw["shimmer_percent"],
        hnr_db=acoustic_raw["hnr_db"],
        voice_quality_score=acoustic_raw["voice_quality_score"],
        f1_hz=acoustic_raw.get("f1_hz"),
        f2_hz=acoustic_raw.get("f2_hz"),
    )

    return AttemptResult(
        attempt_id=str(uuid.uuid4()),
        session_id=session_id,
        child_id=child_id,
        timestamp=datetime.now(),
        target_word=target_word,
        target_phonemes=target_phonemes,
        transcript=transcript,
        detected_phonemes=detected_phonemes,
        phoneme_scores=phoneme_scores,
        acoustic=acoustic,
        composite_score=composite,
        repeat_needed=repeat_needed,
        attempt_number=attempt_number,
        feedback=feedback,
        condition=condition,
    )
