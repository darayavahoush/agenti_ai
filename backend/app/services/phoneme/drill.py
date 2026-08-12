from app.services.phoneme.data import PHONEME_DATA, ACOUSTIC_FEEDBACK_RULES, DRILL_SEQUENCE_RULES
from app.services.phoneme.svg import get_phoneme_card


def get_acoustic_feedback(acoustic: dict, condition: str = "autism") -> list:
    """Return list of acoustic tips based on measured params."""
    tips = []
    for rule in ACOUSTIC_FEEDBACK_RULES:
        # Skip flat pitch penalty for autism
        if rule["id"] == "flat_pitch" and condition == "autism":
            continue
        try:
            if rule["condition"](acoustic):
                tips.append({"tip": rule["tip"], "mood": rule["mood"]})
        except Exception:
            continue
    return tips


def build_drill_sequence(struggling_phonemes: list, condition: str = "autism") -> list:
    """Build a drill sequence for phonemes the child is struggling with."""
    sequence = []
    for phoneme in struggling_phonemes[:DRILL_SEQUENCE_RULES["phonemes_per_session"]]:
        card = get_phoneme_card(phoneme)
        if card:
            sequence.append({
                **card,
                "drill_attempts": 0,
                "drill_passed": False,
                "condition": condition,
            })
    return sequence


def detect_struggling_phonemes(attempt_history: list) -> list:
    """
    From a list of attempt results, find which phonemes
    the child consistently gets wrong.
    """
    error_counts = {}
    for attempt in attempt_history:
        matches = attempt.get("phoneme_scores", {}).get("matches", [])
        for match in matches:
            if not match.get("correct"):
                ph = match.get("expected", "")
                if ph:
                    error_counts[ph] = error_counts.get(ph, 0) + 1

    # Return phonemes wrong more than once, sorted by frequency
    struggling = [p for p, c in sorted(error_counts.items(), key=lambda x: -x[1]) if c >= 2]
    return struggling


def should_enter_drill_mode(attempt_history: list) -> bool:
    """Check if child has failed enough times to enter drill mode."""
    if len(attempt_history) < DRILL_SEQUENCE_RULES["max_attempts_before_drill"]:
        return False
    recent = attempt_history[-DRILL_SEQUENCE_RULES["max_attempts_before_drill"]:]
    avg_score = sum(a.get("composite_score", 0) for a in recent) / len(recent)
    return avg_score < DRILL_SEQUENCE_RULES["accuracy_threshold"]


def get_encouragement_message(score: float, attempt_number: int, condition: str) -> dict:
    """Get contextual encouragement based on score and attempt number."""
    if score >= 80:
        return {
            "message": "Excellent! You got it!",
            "mood": "celebrate",
            "action": "next_word"
        }
    elif score >= 60:
        if attempt_number < 3:
            return {
                "message": "Good try! Let us try one more time.",
                "mood": "encourage",
                "action": "retry"
            }
        else:
            return {
                "message": "Well done for trying. Let us practise the sounds separately.",
                "mood": "encourage",
                "action": "drill"
            }
    elif score >= 40:
        return {
            "message": "Keep going. Let us break this down together.",
            "mood": "instruction",
            "action": "drill"
        }
    else:
        return {
            "message": "Let me show you how to make this sound.",
            "mood": "instruction",
            "action": "support"
        }
