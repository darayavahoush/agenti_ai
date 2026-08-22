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


ENCOURAGEMENT_MESSAGES = {
    "excellent": {
        "english": "Excellent! You got it!",
        "hindi": "शाबाश! आपने कर दिखाया!",
        "kannada": "ಭಲೇ! ನೀವು ಮಾಡಿದಿರಿ!",
    },
    "retry": {
        "english": "Good try! Let us try one more time.",
        "hindi": "अच्छा प्रयास! एक बार और करके देखते हैं।",
        "kannada": "ಒಳ್ಳೆಯ ಪ್ರಯತ್ನ! ಇನ್ನೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸೋಣ।",
    },
    "drill": {
        "english": "Well done for trying. Let us practise the sounds separately.",
        "hindi": "प्रयास करने के लिए शाबाश। आइए ध्वनियों को अलग से सीखें।",
        "kannada": "ಪ್ರಯತ್ನಿಸಿದ್ದಕ್ಕೆ ಭಲೇ. ಧ್ವನಿಗಳನ್ನು ಪ್ರತ್ಯೇಕವಾಗಿ ಅಭ್ಯಾಸ ಮಾಡೋಣ।",
    },
    "breakdown": {
        "english": "Keep going. Let us break this down together.",
        "hindi": "जारी रखें। आइए इसे मिलकर समझते हैं।",
        "kannada": "ಮುಂದುವರಿಯಿರಿ. ಇದನ್ನು ಒಟ್ಟಿಗೆ ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳೋಣ।",
    },
    "support": {
        "english": "Let me show you how to make this sound.",
        "hindi": "मैं आपको यह ध्वनि बनाना सिखाता हूँ।",
        "kannada": "ಈ ಧ್ವನಿಯನ್ನು ಹೇಗೆ ಮಾಡುವುದು ಎಂದು ತೋರಿಸುತ್ತೇನೆ।",
    },
}

FEEDBACK_MESSAGES = {
    "good_try": {
        "english": "Good try! Keep practising this sound.",
        "hindi": "अच्छा प्रयास! इस ध्वनि का अभ्यास जारी रखें।",
        "kannada": "ಒಳ್ಳೆಯ ಪ್ರಯತ್ನ! ಈ ಧ್ವನಿಯ ಅಭ್ಯಾಸ ಮುಂದುವರಿಸಿ।",
    },
    "flow": {
        "english": "Good try. Now let the sounds flow together more smoothly.",
        "hindi": "अच्छा प्रयास। अब ध्वनियों को एक साथ और सहजता से बोलने की कोशिश करें।",
        "kannada": "ಒಳ್ಳೆಯ ಪ್ರಯತ್ನ. ಈಗ ಧ್ವನಿಗಳನ್ನು ಒಟ್ಟಿಗೆ ಸರಳವಾಗಿ ಹೇಳಿ.",
    },
    "breath": {
        "english": "Take a breath and try again. Make sure your voice is nice and clear.",
        "hindi": "एक सांस लें और फिर कोशिश करें। आपकी आवाज़ साफ़ और स्पष्ट होनी चाहिए।",
        "kannada": "ಉಸಿರು ತೆಗೆದುಕೊಂಡು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. ನಿಮ್ಮ ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿರಲಿ.",
    },
    "steady": {
        "english": "Try to keep your voice steady and smooth, like a long smooth train track.",
        "hindi": "अपनी आवाज़ को स्थिर और सहज रखने की कोशिश करें।",
        "kannada": "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಸ್ಥಿರ ಮತ್ತು ಸರಳವಾಗಿ ಇಡಿ.",
    },
}

ACOUSTIC_TIPS = {
    "english": [
        "Good try. Now let the sounds flow together more smoothly.",
        "Take a breath and try again. Make sure your voice is nice and clear.",
        "Try to keep your voice steady and smooth, like a long smooth train track.",
        "Slow down a little. Take it one sound at a time.",
        "Open your mouth a little more when you speak.",
    ],
    "hindi": [
        "अच्छा प्रयास। अब ध्वनियों को एक साथ सहजता से बोलें।",
        "एक सांस लें और फिर कोशिश करें। आवाज़ साफ़ होनी चाहिए।",
        "अपनी आवाज़ को स्थिर और सहज रखें।",
        "थोड़ा धीरे बोलें। एक-एक ध्वनि पर ध्यान दें।",
        "बोलते समय मुँह थोड़ा और खोलें।",
    ],
    "kannada": [
        "ಒಳ್ಳೆಯ ಪ್ರಯತ್ನ. ಧ್ವನಿಗಳನ್ನು ಒಟ್ಟಿಗೆ ಸರಳವಾಗಿ ಹೇಳಿ.",
        "ಉಸಿರು ತೆಗೆದುಕೊಂಡು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿರಲಿ.",
        "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಸ್ಥಿರ ಮತ್ತು ಸರಳವಾಗಿ ಇಡಿ.",
        "ಸ್ವಲ್ಪ ನಿಧಾನವಾಗಿ ಮಾತನಾಡಿ. ಒಂದೊಂದು ಧ್ವನಿಯನ್ನು ಗಮನಿಸಿ.",
        "ಮಾತನಾಡುವಾಗ ಬಾಯಿಯನ್ನು ಸ್ವಲ್ಪ ಹೆಚ್ಚು ತೆರೆಯಿರಿ.",
    ],
}

def get_encouragement_message(score: float, attempt_number: int, condition: str, language: str = "english") -> dict:
    """Get contextual encouragement based on score and attempt number."""
    lang = language if language in ("english", "hindi", "kannada") else "english"
    if score >= 80:
        return {
            "message": ENCOURAGEMENT_MESSAGES["excellent"][lang],
            "mood": "celebrate",
            "action": "next_word"
        }
    elif score >= 60:
        if attempt_number < 3:
            return {
                "message": ENCOURAGEMENT_MESSAGES["retry"][lang],
                "mood": "encourage",
                "action": "retry"
            }
        else:
            return {
                "message": ENCOURAGEMENT_MESSAGES["drill"][lang],
                "mood": "encourage",
                "action": "drill"
            }
    elif score >= 40:
        return {
            "message": ENCOURAGEMENT_MESSAGES["breakdown"][lang],
            "mood": "instruction",
            "action": "drill"
        }
    else:
        return {
            "message": ENCOURAGEMENT_MESSAGES["support"][lang],
            "mood": "instruction",
            "action": "support"
        }
