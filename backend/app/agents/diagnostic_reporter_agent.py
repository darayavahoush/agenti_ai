import os
import json
from app.state.assessment_state import AssessmentState
import logging

logger = logging.getLogger(__name__)



class DiagnosticReporterAgent:
    """
    Agent responsible for compiling the final Speech-Language Pathology (SLP)
    diagnostic report combining articulation patterns and vocal characteristics.
    """

    def analyze(self, state: AssessmentState) -> AssessmentState:
        patient_name = state.get("patient_name") or "Child"
        target_word = state.get("target_word", "")
        accuracy = state.get("accuracy") or 0
        severity_score = state.get("severity_score") or "Normal"
        error_patterns = state.get("error_patterns") or []
        # NOTE: was state.get("reasoning"), but "reasoning" is the audio-channel
        # selection note from speech_analysis_agent (e.g. "Isolated child voice
        # segment selected") -- and since vocal_acoustic_agent runs in the same
        # parallel graph step and used to also write to "reasoning", whichever
        # of the two ran last silently clobbered the other's value. Both agents
        # now write to their own state keys (see vocal_acoustic_agent.py), so
        # this reads the vocal-specific one instead of whatever happened to
        # win the race.
        vocal_reasoning = state.get("vocal_reasoning") or ""
        metrics = state.get("recommendations") or []

        # Try to use OpenAI if key is present and package is installed
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)

                prompt = f"""
                You are a Pediatric Speech-Language Pathologist (SLP) writing an Assessment report.
                Write a child-friendly, encouraging but clinically informative diagnostic summary.

                Patient Name: {patient_name}
                Target Word: {target_word}
                Accuracy Score: {accuracy}%
                Severity Classification: {severity_score}
                Speech Error Patterns Detected: {", ".join(error_patterns) if error_patterns else "None"}
                Vocal Acoustic Notes: {vocal_reasoning}
                Acoustic Metrics: {", ".join(metrics)}

                Provide a JSON response containing:
                {{
                    "diagnostic_report": "The formal clinician summary report paragraph."
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a diagnostic reporter agent compiler."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                # NOTE: this used to reference `data`, which was never
                # assigned anywhere in this function -- the OpenAI response
                # was fetched into `response` but never parsed. That raised a
                # bare NameError on every single call whenever OPENAI_API_KEY
                # was set, silently caught by the except below, so this
                # branch could never succeed: every assessment got the
                # generic Expert System report instead of the intended
                # LLM-personalized one, with no visible error to the user.
                data = json.loads(response.choices[0].message.content)
                return {
                    "diagnostic_report": data.get("diagnostic_report")
                }
            except Exception as e:
                logger.info(f"OpenAI Diagnostic Reporter Error: {e}. Falling back to Expert System.")

        # Expert System Fallback Report Compiler
        report_sections = []
        report_sections.append(
            f"Assessment summary for {patient_name} practicing '{target_word}'. "
            f"Overall pronunciation matches the target at {accuracy}%, indicating a '{severity_score}' status."
        )

        if error_patterns:
            report_sections.append(
                f"We observed the following phonological patterns: {', '.join(error_patterns)}. "
                "These patterns are developmental and will benefit from targeted sound practice."
            )
        else:
            report_sections.append(
                "No major phonological errors or articulation replacements were identified. Good sound structure!"
            )

        if vocal_reasoning:
            report_sections.append(
                f"Acoustic feedback: {vocal_reasoning} "
                f"Core vocal metrics: {', '.join(metrics)}."
            )

        return {
            "diagnostic_report": " ".join(report_sections)
        }
