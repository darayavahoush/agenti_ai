"""
routers/vaakmirror/sessions.py — VaakMirror session/attempt logging.

Extends the adaptive-difficulty agent (already wired into Chime and
BreathQuest -- see routers/breath_agent.py) to VaakMirror: every logged
Attempt is *also* written to the shared retraining.data_store as an
RLTrainingEvent, so VaakMirror's sound-practice attempts feed the same
per-child tabular-Q/PPO/RecurrentPPO ladder BreathQuest and Chime already
train against (agent/child_q_store.py keys tables by child_id only, so
this generalizes a child's "difficulty" judgement across all three apps).

Mapping from VaakMirror's Attempt shape onto the shared RLTrainingEvent
schema (see retraining/models.py):
- level_id: "vm_{sound_id}" -- one shared level per sound across all three
  VaakMirror sub-games (mirror_mirror/tongue_tamer/lip_sync_hero), not
  split per-game, so practicing "sh" in any of the three counts toward the
  same per-sound history. Falls back to "vm_unknown_{game}" on the rare
  attempt with no sound_id, so it still logs somewhere rather than being
  silently dropped, without polluting real per-sound windows.
- score / is_valid_attempt: uses Attempt.score when the caller provided
  one; otherwise binary from outcome (passed/caught -> 1.0, missed ->
  0.0), matching weekly_summary.py's _VM_SUCCESS_OUTCOMES definition of
  success. is_valid_attempt is always True -- every AttemptOutcome value
  represents a real completed attempt; there's no "malformed/discarded"
  state in this schema the way some other games have.
- attempt_number: count of this session's prior attempts at this same
  level_id (0-indexed), computed before insert so the new attempt isn't
  counted against itself -- matches BreathQuest/Chime's convention that
  attempt_number == 0 marks the start of a new session, which
  agent/service.py's detect_trend() relies on to segment cross-session
  history.
- quit_flag: always False -- VaakMirror's Attempt model has no signal for
  "gave up mid-attempt" today. Revisit if the frontend starts
  distinguishing an abandoned attempt from a completed one.
- threshold_at_time / action: None -- VaakMirror doesn't have an adaptive
  difficulty *decision* endpoint yet (this pass wires up event *logging*
  only, i.e. training-data collection). Adding a decide()-equivalent
  endpoint for VaakMirror the way breath_agent.py did for BreathQuest is a
  natural next step, deliberately out of scope here.
- severity_numeric / is_targeted_sound: same diagnostic-context lookup
  chime.py/breath_agent.py use, keyed off assessment_patient_id -- looked
  up here via BreathQuestPatient, since VaakMirror's own auth (see
  vaakmirror_auth.py) issues tokens against breathquest_patients.id
  directly and doesn't carry assessment_patient_id itself.
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.vaakmirror_auth import get_current_patient_id
from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient
from app.models.vaakmirror_models import Attempt, AttemptOutcome, VaakMirrorSession
from app.schemas.vaakmirror_schemas import AttemptCreate, AttemptOut, SessionCreate, SessionOut

from app.retraining import data_store
from app.retraining.scheduler import run_retrain_if_due
from agent.diagnostic_client import get_diagnostic_context

router = APIRouter(tags=["vaakmirror-sessions"])

DB_PATH = data_store.DEFAULT_DB_PATH
_VM_SUCCESS_OUTCOMES = (AttemptOutcome.passed, AttemptOutcome.caught)


def _vm_level_id(sound_id: str | None, game) -> str:
    if sound_id:
        return f"vm_{sound_id}"
    return f"vm_unknown_{game.value}"


@router.post("/sessions", response_model=SessionOut)
async def create_session(
    payload: SessionCreate,
    patient_id: str = Depends(get_current_patient_id),
    db: AsyncSession = Depends(get_db),
):
    session = VaakMirrorSession(patient_id=patient_id, game=payload.game)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/sessions/{session_id}/attempts", response_model=AttemptOut)
async def log_attempt(
    session_id: int,
    payload: AttemptCreate,
    background_tasks: BackgroundTasks,
    patient_id: str = Depends(get_current_patient_id),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(VaakMirrorSession, session_id)
    if not session or session.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Session not found")

    level_id = _vm_level_id(payload.sound_id, session.game)

    prior_count_result = await db.execute(
        select(func.count()).select_from(Attempt).where(
            Attempt.session_id == session_id,
            Attempt.sound_id == payload.sound_id,
        )
    )
    attempt_number = prior_count_result.scalar_one()

    attempt = Attempt(session_id=session_id, **payload.model_dump())
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    if payload.score is not None:
        rl_score = payload.score
    else:
        rl_score = 1.0 if payload.outcome in _VM_SUCCESS_OUTCOMES else 0.0

    patient_result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.id == patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if patient and patient.assessment_patient_id:
        severity_numeric, targeted_quests = get_diagnostic_context(patient.assessment_patient_id)
    else:
        severity_numeric, targeted_quests = 0.0, frozenset()
    is_targeted_sound = level_id in targeted_quests

    await asyncio.to_thread(
        data_store.add_event,
        child_id=patient_id,
        level_id=level_id,
        attempt_number=attempt_number,
        score=rl_score,
        is_valid_attempt=True,
        threshold_at_time=None,
        action=None,
        quit_flag=False,
        raw_features={
            "place": payload.place,
            "manner": payload.manner,
            "voicing": payload.voicing,
            "game": session.game.value,
            "outcome": payload.outcome.value,
        },
        severity_numeric=severity_numeric,
        is_targeted_sound=is_targeted_sound,
        policy_used=None,
        downgrade_reason=None,
        recommended_action=None,
        recommendation_message=None,
        db_path=DB_PATH,
    )

    background_tasks.add_task(run_retrain_if_due, DB_PATH)

    return attempt


@router.patch("/sessions/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: int,
    patient_id: str = Depends(get_current_patient_id),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(VaakMirrorSession, session_id)
    if not session or session.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session
