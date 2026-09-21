import logging

from app.services.alphabet_sounds import LETTERS, strip_stress
from app.state.alphabet_state import AlphabetState

logger = logging.getLogger(__name__)

_NO_SPEECH = {"", "no speech detected"}


class AlphabetFocusAgent:
    """
    Narrows the (reused) speech + articulation analysis of a keyword down to
    the ONE sound the child was asked about, e.g. the /b/ in "ball".

    Runs after SpeechAnalysisAgent and ArticulationDiagnosticAgent in the
    alphabet graph. It only reads what they produced (phoneme_matches,
    spoken_word, accuracy, error_patterns) and writes `letter_result`; it
    never re-runs speech recognition.
    """

    def analyze(self, state: AlphabetState) -> dict:
        letter = str(state.get("letter") or "").upper()
        spec = LETTERS.get(letter)
        if spec is None:
            return {"letter_result": None, "error": f"'{letter}' is not a probe letter"}

        spoken_word = str(state.get("spoken_word") or "").strip()
        base = {
            "letter": letter,
            "word": spec["word"],
            "sound_id": spec["vm"],
            "group": spec["group"],
            "next": list(spec["next"]),
            "spoken_word": spoken_word,
            "word_accuracy": state.get("accuracy"),
            "error_patterns": list(state.get("error_patterns") or []),
        }

        if spoken_word.lower() in _NO_SPEECH:
            return {"letter_result": {**base, "status": "no_speech", "correct": None,
                                      "heard_as": None, "score": None,
                                      "message": "I couldn't hear anything. Tap the mic and try again."}}

        target = spec["arpa"]
        hit = next(
            (m for m in (state.get("phoneme_matches") or [])
             if isinstance(m, dict) and strip_stress(m.get("expected")) == target),
            None,
        )
        if hit is None:
            # The keyword's phonemes didn't include the target (dictionary gap):
            # say so rather than guessing a verdict.
            return {"letter_result": {**base, "status": "unscored", "correct": None,
                                      "heard_as": None, "score": None,
                                      "message": "I couldn't check this one. You can move on to the next letter."}}

        correct = bool(hit.get("correct"))
        heard = strip_stress(hit.get("spoken")) or None
        result = {
            **base,
            "status": "ok" if correct else "missed",
            "correct": correct,
            "heard_as": None if correct else heard,
            # 1.0 clean, 0.0 missed. The word-level accuracy is reported
            # separately: a slip on another sound shouldn't fail this letter.
            "score": 1.0 if correct else 0.0,
            "message": (
                f"Clear {letter} sound! Nice work."
                if correct else
                (f"That sounded a bit like \u201c{heard.lower()}\u201d. "
                 f"Look at the mouth picture and try \u201c{spec['word']}\u201d again.")
                if heard else
                f"I couldn't hear the {letter} sound clearly. Try \u201c{spec['word']}\u201d again."
            ),
        }
        return {"letter_result": result}
