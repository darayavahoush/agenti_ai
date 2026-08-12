"""
services/assessment_lookup.py — in-process replacement for quest-games'
HTTP-based core.assessment_client.get_latest_assessment (and the similarly-
shaped agent/diagnostic_client.py used by breath_agent.py). Both of those
did an HTTP round trip + ASSESSMENT_SERVICE_API_KEY auth to what was, at the
time, a separate microservice.

That's no longer true here: Assessment's data (app/routes/assessment.py,
app/models/session.py) lives directly in this same backend process as of
the backend-merge reversal (see main.py's 2026-08-11 comments). So rather
than looping BreathQuest's dashboard back out over HTTP to itself, this
queries the same SessionModel directly.

Mirrors assessment.py's GET /assessment/patients/{patient_id}/latest
(service-to-service route, kept as-is there since other external callers
may still use it) — same filter, same ordering, same three fields — just
in-process instead of over the wire.

Deliberately sync (SessionLocal, not AsyncSession) to match assessment.py's
own pattern (see that file's create_patient_for_therapist docstring for why
sync there). Callers in async routes must wrap this in asyncio.to_thread,
same as the rest of this pass's sync-in-async cleanup (retraining/db.py,
retraining/data_store.py callers).
"""

from app.database import SessionLocal
from app.models.session import Session as SessionModel


def get_latest_assessment(assessment_patient_id: str) -> dict | None:
    """Most recent word_practice diagnostic session for this Assessment
    patient id, or None if this patient has no assessment on file yet.
    `assessment_patient_id` here is BreathQuestPatient.assessment_patient_id
    (the FK into Assessment's patients table), not a BreathQuest patient id."""
    db = SessionLocal()
    try:
        session = (
            db.query(SessionModel)
            .filter(
                SessionModel.patient_id == assessment_patient_id,
                SessionModel.session_type == "word_practice",
            )
            .order_by(SessionModel.created_at.desc())
            .first()
        )
        if session is None:
            return None
        return {
            "session_id": session.id,
            "patient_id": session.patient_id,
            "severity_classification": session.severity_classification,
            "targeted_quests": session.targeted_quests,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }
    finally:
        db.close()
