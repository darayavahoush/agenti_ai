import os
import json
from app.state.speech_state import SpeechState


class SupervisorAgent:
    """
    Supervisor Agent responsible for coordinating the multi-agent execution flow.
    Evaluates vocal characteristics and pronunciation to decide the next agent step
    and provides clinical decision reasoning.
    """

    def analyze(self, state: SpeechState) -> SpeechState:
        accuracy = state.get("accuracy") or 0
        pitch = state.get("pitch") or 0
        loudness = state.get("loudness") or 0
        target_word = state.get("target_word", "")
        intensive_triggered = state.get("intensive_practice_triggered") or False

        # Try to use OpenAI if key is present and package is installed
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)

                prompt = f"""
                You are the Supervisor Agent of an AI Speech Therapy system.
                Analyze the session details and determine who goes next.

                Session State:
                Target Word: {target_word}
                Accuracy: {accuracy}%
                Pitch Mean: {pitch} Hz
                Loudness Mean: {loudness}
                Intensive practice triggered by history: {intensive_triggered}

                Decisions:
                1. If pitch is < 50 or loudness < 0.002, suspect whispering. Ask to speak louder and repeat (next_agent='session_planning').
                2. If intensive_practice_triggered is True, route to intensive drills (next_agent='intensive_practice').
                3. If accuracy is < 70, route to clinical tips (next_agent='therapy_recommendation').
                4. If accuracy is >= 70, child mastered the word, route to planner directly (next_agent='session_planning').

                Response JSON Format:
                {{
                    "reasoning": "Conversational, human SLP-style reasoning explaining the decision to the developer/therapist (e.g. 'Vocal check: Volume is quiet... Let's speak up')",
                    "next_agent": "intensive_practice" | "therapy_recommendation" | "session_planning",
                    "recommendations": ["Directives to the patient/system"]
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a clinical supervisor agent orchestrating pediatric SLP therapy."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content)
                state["reasoning"] = data.get("reasoning")
                state["next_agent"] = data.get("next_agent", "session_planning")
                state["recommendations"] = data.get("recommendations", [])
                return state
            except Exception as e:
                print(f"OpenAI Supervisor Error: {e}. Falling back to Rule-Based Supervisor.")

        # Rule-Based SLP Decision Engine Fallback
        reasoning_steps = []
        recommendations = []
        next_agent = "session_planning"

        # Decision 1: Volume/Whispering check
        if loudness < 0.002 or pitch < 50:
            next_agent = "session_planning"
            reasoning_steps.append(
                "Vocal check: Speech volume was very quiet. "
                "Let's speak up loud and clear like a lion next time!"
            )
            recommendations.append("Speak up nice and loud for the microphone!")
            state["repeat_word"] = True

        # Decision 2: Intensive practice check
        elif intensive_triggered:
            next_agent = "intensive_practice"
            reasoning_steps.append(
                f"Practice streak: We've spent a few turns practicing '{target_word}'. "
                "Let's switch to specialized visual drills to build muscle memory!"
            )
            recommendations.append("Launch intensive visual and syllable pronunciation drills.")

        # Decision 3: Therapy recommendations check (struggling)
        elif accuracy < 70:
            next_agent = "therapy_recommendation"
            reasoning_steps.append(
                f"Practice check: Accuracy is {accuracy}%. "
                "We are still building confidence, so we've unlocked isolated sound cards to help master this word."
            )
            recommendations.append("Review isolated sound cards for practice.")

        # Decision 4: Success check
        else:
            next_agent = "session_planning"
            reasoning_steps.append(
                f"Super job! Accuracy reached {accuracy}%, which exceeds our mastery goal! "
                "Skipping repetition to try a new challenge."
            )
            recommendations.append("Proceed to the next lesson!")
            state["repeat_word"] = False

        state["reasoning"] = " | ".join(reasoning_steps)
        state["next_agent"] = next_agent
        state["recommendations"] = recommendations

        return state
