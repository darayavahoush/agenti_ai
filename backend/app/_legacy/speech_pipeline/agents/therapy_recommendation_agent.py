import os
import json
from app.state.speech_state import SpeechState


class TherapyRecommendationAgent:
    """
    Agent utilizing an LLM (with rule-based expert fallback) to read pronunciation
    errors and generate therapist observations, suggested exercises, and repetition decisions.
    """

    def analyze(self, state: SpeechState) -> SpeechState:
        accuracy = state.get("accuracy") or 0
        target_word = state.get("target_word", "")
        spoken_word = state.get("spoken_word", "")
        phoneme_matches = state.get("phoneme_matches") or []
        loudness = state.get("loudness") or 0

        # Try to use OpenAI if key is present and package is installed
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)

                prompt = f"""
                Analyze the speech therapy session:
                Target Word: {target_word}
                Spoken Word: {spoken_word}
                Pronunciation Accuracy: {accuracy}%
                Loudness Mean: {loudness}
                Phoneme Matches: {json.dumps(phoneme_matches)}

                Respond in JSON format:
                {{
                    "therapist_observations": "Detailed clinical observation on pronunciation issues.",
                    "suggested_exercises": ["List", "of", "suggested", "exercises"],
                    "repeat_word": true/false
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert pediatric Speech-Language Pathologist (SLP)."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)
                state["therapist_observations"] = data.get("therapist_observations")
                state["suggested_exercises"] = data.get("suggested_exercises", [])
                state["repeat_word"] = data.get("repeat_word", accuracy < 70)
                return state
            except Exception as e:
                # Log error and fall back to rule-based system
                print(f"OpenAI SLP Agent Error: {e}. Falling back to Expert System.")

        # Expert System Fallback
        incorrect_phonemes = [
            m["expected"] for m in phoneme_matches if not m.get("correct")
        ]

        observations = []
        exercises = []
        repeat = True

        if loudness < 0.005:
            observations.append(
                f"Audio volume is low ({loudness:.4f}). The child may be whispering, speaking "
                "too far from the mic, or shy."
            )
            exercises.extend(["Belly breathing voice projection", "Microphone distance test"])

        if accuracy < 50:
            observations.append(
                f"Pronunciation accuracy is low ({accuracy}%). The child is struggling with the core "
                f"structure of '{target_word}'."
            )
            exercises.extend(["Syllable-clapping breakdown", "Mouth shape mirroring visual match"])
            repeat = True
        elif accuracy < 70:
            observations.append(
                f"Pronunciation is developing ({accuracy}%). The child correctly voiced some elements but "
                f"failed key phonemes: {', '.join(incorrect_phonemes) if incorrect_phonemes else 'transitions'}."
            )
            exercises.extend(["Isolated phoneme repetition", "Slow-motion word elongation"])
            repeat = True
        else:
            observations.append(
                f"Excellent pronunciation ({accuracy}%). Minor accent or voicing variants detected. "
                "Good vocal projection."
            )
            exercises.extend(["Sentence context integration"])
            repeat = False

        state["therapist_observations"] = " ".join(observations)
        state["suggested_exercises"] = exercises
        state["repeat_word"] = repeat

        return state
