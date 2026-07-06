from app.state.speech_state import SpeechState


class IntensivePracticeAgent:
    """
    Agent triggered when a child exhibits repeated struggles on the same target word
    across multiple sessions. Generates visual break down and intensive SLP drills.
    """

    def analyze(self, state: SpeechState) -> SpeechState:
        target_word = state.get("target_word", "")
        phoneme_matches = state.get("phoneme_matches") or []

        # Find specific struggling phonemes
        struggle_phonemes = [
            m["expected"] for m in phoneme_matches if not m.get("correct")
        ]

        phoneme_focus = (
            f"/{'/ and /'.join(struggle_phonemes)}/"
            if struggle_phonemes
            else "transitions and flow"
        )

        message = (
            f"🎯 INTENSIVE DRILL ACTIVATED: The child is experiencing repeated blockages with '{target_word}'.\n"
            f"Therapeutic Focus: Isolated muscle drills for {phoneme_focus}.\n"
            f"Recommended Protocol: 3x slow-motion visual modeling, followed by syllable separation "
            f"('{target_word}' broken down into visual mouth shapes)."
        )

        state["intensive_practice_message"] = message
        # Ensure repeat_word is True since intensive drill is running
        state["repeat_word"] = True

        return state
