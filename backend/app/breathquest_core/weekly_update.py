"""
app/breathquest_core/weekly_update.py — Weekly parent progress-email
trigger, following the same lazy-checkpoint shape as
app/retraining/scheduler.py's run_retrain_if_due: this project has no
real job scheduler (no Celery/APScheduler/cron -- the Dockerfile's CMD
runs a single uvicorn process, nothing else), so instead of a true
"every Monday at 9am" schedule, this checks opportunistically on every
kid_login whether 7+ days have passed since the last send, and if so,
sends and stamps a new checkpoint (BreathQuestPatient.last_weekly_email_sent_at).

Content: a progress digest (sessions completed, levels practiced, average
breath consistency) if the kid had any completed GameSessions in the
window, or a gentle nudge email if they didn't -- never silence, per the
"send something every week either way" requirement.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import BreathQuestPatient, GameSession
from app.services.email import send_weekly_progress_email, send_weekly_nudge_email

logger = logging.getLogger("uvicorn.error")

WEEKLY_INTERVAL = timedelta(days=7)


async def maybe_send_weekly_update(patient: BreathQuestPatient, db: AsyncSession) -> None:
    """Best-effort: any failure here must never affect login. Caller
    (kid_login) wraps this in its own try/except as an extra safety net,
    but this function also swallows its own email-send errors so a bad
    checkpoint stamp never happens on a failed send (next login retries)."""
    if not patient.parent_email:
        return

    now = datetime.now(timezone.utc)
    last_sent = patient.last_weekly_email_sent_at
    if last_sent is not None and (now - last_sent) < WEEKLY_INTERVAL:
        return

    window_start = last_sent or (now - WEEKLY_INTERVAL)

    result = await db.execute(
        select(GameSession).where(
            GameSession.patient_id == patient.id,
            GameSession.started_at >= window_start,
            GameSession.completed.is_(True),
        )
    )
    sessions = result.scalars().all()

    try:
        if sessions:
            session_count = len(sessions)
            consistencies = [
                s.breath_consistency for s in sessions if s.breath_consistency is not None
            ]
            avg_consistency = (
                round(sum(consistencies) / len(consistencies)) if consistencies else None
            )
            levels_practiced = sorted({
                s.level_id.value if hasattr(s.level_id, "value") else str(s.level_id)
                for s in sessions
            })
            send_weekly_progress_email(
                patient.parent_email,
                patient.first_name,
                session_count=session_count,
                levels_practiced=levels_practiced,
                avg_consistency=avg_consistency,
            )
        else:
            send_weekly_nudge_email(patient.parent_email, patient.first_name)
    except Exception as exc:
        logger.warning(
            "Weekly update email failed for %s (patient %s): %s",
            patient.parent_email, patient.id, exc,
        )
        return  # don't stamp the checkpoint on a failed send -- retry next login

    patient.last_weekly_email_sent_at = now
    await db.commit()
