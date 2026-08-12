import os
import json
from app.state.assessment_state import AssessmentState


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
        vocal_reasoning = state.get("reasoning") or ""
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
                return {
                    "diagnostic_report": data.get("diagnostic_report")
                }
            except Exception as e:
                print(f"OpenAI Diagnostic Reporter Error: {e}. Falling back to Expert System.")

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
