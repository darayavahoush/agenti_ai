from app.state.speech_state import SpeechState


class SessionPlanningAgent:
    """
    Agent responsible for selecting the next therapy word and practice exercise,
    adjusting difficulty levels based on the child's accuracy and historical trends.
    """

    WORD_PROGRESSION = [
        "apple",
        "ball",
        "cat",
        "dog",
        "sun",
        "ship",
        "boat",
        "umbrella",
        "teacher"
    ]

    def analyze(self, state: SpeechState) -> SpeechState:
        target_word = state.get("target_word", "")
        repeat_word = state.get("repeat_word") or False
        diff_adjustment = state.get("difficulty_adjustment") or "maintain"
        accuracy = state.get("accuracy") or 0

        # Determine next word
        if repeat_word:
            state["next_word"] = target_word
            state["session_difficulty"] = "Syllable Level" if accuracy < 50 else "Word Level"
            state["next_exercise"] = "Target word syllable breakdown repetition"
        else:
            # Move to next word in the progression
            try:
                current_idx = self.WORD_PROGRESSION.index(target_word.lower())
                next_idx = (current_idx + 1) % len(self.WORD_PROGRESSION)
                state["next_word"] = self.WORD_PROGRESSION[next_idx]
            except ValueError:
                # Target word is not in default progression list, fallback
                state["next_word"] = "umbrella"

            # Set difficulty and exercise based on adjustment recommendations
            if diff_adjustment == "increase":
                state["session_difficulty"] = "Sentence Level"
                state["next_exercise"] = f"Use '{state['next_word']}' in a complete spoken sentence."
            elif diff_adjustment == "decrease":
                state["session_difficulty"] = "Phoneme Level"
                state["next_exercise"] = f"Isolate starting sound of '{state['next_word']}'."
            else:
                state["session_difficulty"] = "Word Level"
                state["next_exercise"] = f"Full word pronunciation practice of '{state['next_word']}'."

        return state
