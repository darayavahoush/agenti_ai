from app.state.speech_state import SpeechState
from app.database import SessionLocal
from app.models.patient import Patient
from app.models.session import Session as SessionModel


class ProgressEvaluationAgent:
    """
    Agent responsible for evaluating historical sessions to detect
    pronunciation improvement trends and trigger intensive practice.
    """

    def analyze(self, state: SpeechState) -> SpeechState:
        patient_name = state.get("patient_name")
        target_word = state.get("target_word", "")
        current_accuracy = state.get("accuracy") or 0

        state["intensive_practice_triggered"] = False
        state["difficulty_adjustment"] = "maintain"

        if not patient_name:
            state["progress_report"] = "No patient name provided. Cannot evaluate history."
            return state

        db = SessionLocal()
        try:
            # Query patient details
            clean_name = patient_name.strip()
            patient = db.query(Patient).filter(
                Patient.name.ilike(clean_name)
            ).first()

            if not patient:
                state["progress_report"] = "New patient registered. No history found."
                return state

            # Fetch recent sessions (e.g. past 5 sessions)
            past_sessions = db.query(SessionModel).filter(
                SessionModel.patient_id == patient.id
            ).order_by(SessionModel.created_at.desc()).limit(5).all()

            if not past_sessions:
                state["progress_report"] = "First session completed. Progress tracking will begin on the next session."
                return state

            accuracies = [s.accuracy for s in past_sessions if s.accuracy is not None]
            
            # 🎯 DETECT REPEATED MISTAKES (3 sessions struggling with same word)
            struggle_count = 0
            for session in past_sessions:
                if session.target_word and session.target_word.lower() == target_word.lower():
                    if session.accuracy is not None and session.accuracy < 70:
                        struggle_count += 1
                    else:
                        break # Streak broken by successful session

            # Include the current session struggle
            if current_accuracy < 70:
                struggle_count += 1

            therapist_alert = ""
            if struggle_count >= 3:
                state["intensive_practice_triggered"] = True
                therapist_alert = f" | 🚨 CLINICAL UPDATE: Target word '{target_word}' has been repeated across {struggle_count} sessions. Triggering intensive practice drills."

            # Progress Summary Report
            accuracy_history_str = " -> ".join(str(a) + "%" for a in reversed(accuracies))
            state["progress_report"] = f"Recent scores: {accuracy_history_str}.{therapist_alert} "

            # Difficulty Adjustment Recommendation
            if len(accuracies) >= 3:
                recent_avg = sum(accuracies[:3]) / 3
                if recent_avg >= 90:
                    state["difficulty_adjustment"] = "increase"
                    state["progress_report"] += "Progress: Accuracy is high. Suggesting moving to sentence-level exercises."
                elif recent_avg < 60:
                    state["difficulty_adjustment"] = "decrease"
                    state["progress_report"] += "Progress: Child is finding this word challenging. Suggesting phone-level isolation drills."
                else:
                    state["progress_report"] += "Progress: Score is steady. Suggesting maintaining word-level practice."
            else:
                state["progress_report"] += "More sessions needed to calculate adaptive progression trends."

        except Exception as e:
            state["progress_report"] = f"Progress tracking encounter error: {e}"
        finally:
            db.close()

        return state
