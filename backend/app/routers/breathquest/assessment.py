"""
routers/breathquest/assessment.py — kid-authenticated wrapper around the
Assessment flow (frontend/src/assessment/Assessment.jsx).

Assessment.jsx normally gates itself behind its own name+DOB
login/patient-details screens (POST /patients/, POST /patients/login) --
that made sense when it was a standalone tool, but a kid who already has a
BreathQuest account (JWT via get_current_patient) shouldn't have to enter
their name and birthdate a second time. These two endpoints let
pages/kid/AssessmentGate.jsx bootstrap that same underlying Assessment
`Patient` row using the kid's own identity, then pass the result straight
into Assessment.jsx as authedPatientId/authedPatientName props.

Deliberately sync (SessionLocal, not AsyncSession) for the Patient-table
work, matching assessment_lookup.py's own note on why the Assessment side
of this codebase stays sync.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.database import get_db, SessionLocal
from app.models.breathquest_models import BreathQuestPatient
from app.models.patient import Patient
from app.breathquest_core.deps import get_current_patient
from app.schemas.breathquest_schemas import AssessmentStartOut, AssessmentCompleteRequest
from app.models.vaakmirror_models import VaakMirrorRoundSizeSetting, GameName
from pydantic import BaseModel
from app.routers.breathquest.assessment_lookup import get_latest_assessment
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

router = APIRouter(prefix="/assessment", tags=["assessment"])
logger = logging.getLogger(__name__)


def _predict_games(word_results: list[dict], first_name: str | None) -> dict | None:
    """Sync (the agent may make an OpenAI call) -- always run via
    asyncio.to_thread. Never raises: a failed prediction must not block
    marking the assessment complete or showing the kid their results."""
    try:
        from app.agents.game_predictor_agent import GamePredictorAgent
        return GamePredictorAgent().predict(word_results, first_name)
    except Exception as exc:
        logger.warning("Game prediction failed: %s", exc)
        return None

def _retake_available_at(patient: BreathQuestPatient) -> datetime | None:
    """Retired: retakes are no longer cooldown-gated, so this always
    returns None. Kept as a function (rather than inlined) so
    /assessment/start and /assessment/me/latest don't need their own
    special-casing, and so a cooldown could be reintroduced here again
    later without touching either call site."""
    return None


@router.post("/start", response_model=AssessmentStartOut)
async def start_assessment(
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Auto-links or creates the Assessment-side Patient row for the
    logged-in kid, and returns what AssessmentGate.jsx needs to render
    Assessment.jsx in authed mode.

    already_completed reflects the raw assessment_completed flag -- has
    this kid ever finished one before. It no longer gates whether the
    retake button shows (retakes are always allowed); it only changes
    AssessmentGate.jsx's messaging ("Retake" vs "Start", returning-kid
    copy, hiding the first-timer games preview)."""
    sync_db = SessionLocal()
    try:
        main_patient = None
        if patient.assessment_patient_id:
            main_patient = sync_db.get(Patient, patient.assessment_patient_id)

        if not main_patient or not main_patient.is_active:
            main_patient = Patient(name=patient.first_name)
            sync_db.add(main_patient)
            sync_db.commit()
            sync_db.refresh(main_patient)
    finally:
        sync_db.close()

    if patient.assessment_patient_id != main_patient.id:
        # Newly created (or re-linked) -- persist the link on the async
        # session get_current_patient already resolved `patient` through.
        patient.assessment_patient_id = main_patient.id
        db.add(patient)
        await db.commit()

    return AssessmentStartOut(
        assessment_patient_id=str(main_patient.id),
        first_name=patient.first_name,
        already_completed=patient.assessment_completed,
        retake_available_at=None,
    )


@router.post("/complete", status_code=204)
async def complete_assessment(
    data: AssessmentCompleteRequest,
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Marks the logged-in kid's assessment_completed flag and stores a
    lightweight summary (word count + severity read) for
    AssessmentReport.jsx's free teaser. Also stamps assessment_completed_at
    as a history timestamp of when this completion (first time or a
    retake) happened -- no longer gates anything, since retakes are
    always allowed."""
    from sqlalchemy import select

    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == patient.id))
    row = result.scalar_one()
    row.assessment_completed = True
    row.assessment_completed_at = datetime.now(timezone.utc)
    # After the words are analysed, the game-prediction agent looks ACROSS
    # them (the per-word graph never does) and picks which games help most.
    # Computed server-side from word_results so it can't be spoofed, and
    # stored so the report, therapist views and revisits all read one answer.
    game_predictions = await asyncio.to_thread(_predict_games, data.word_results, row.first_name)
    row.assessment_summary = {
        "words_attempted": data.words_attempted,
        "severity_classification": data.severity_classification,
        "word_results": data.word_results,
        "game_predictions": game_predictions,
        # The Alphabet check is saved by its own endpoint; a word-assessment
        # retake must not wipe it (or the VaakMirror plan built from it).
        **({"alphabet": row.assessment_summary["alphabet"]}
           if (row.assessment_summary or {}).get("alphabet") else {}),
    }
    await db.commit()


@router.get("/me/latest")
async def get_my_latest_assessment(
    patient: BreathQuestPatient = Depends(get_current_patient),
):
    """Kid-authenticated 'my latest results' lookup, for
    pages/kid/AssessmentReport.jsx when revisited later (not just right
    after finishing an assessment via router state). Same in-process query
    dashboard.py already uses, just exposed to the kid themselves.
    retake_available_at is always null now (no cooldown) -- kept in the
    response shape so the frontend doesn't need a schema change if a
    cooldown-style feature ever comes back."""
    if not patient.assessment_patient_id:
        return None
    result = await asyncio.to_thread(get_latest_assessment, str(patient.assessment_patient_id))
    if result is None:
        return None
    result["retake_available_at"] = None
    # word_results only lives in assessment_summary (stamped by
    # POST /assessment/complete), not on the SessionModel row
    # get_latest_assessment reads -- merge it in so a revisit (tapping "My
    # Results" later, with no router state) still gets the same detailed
    # per-word breakdown as right after finishing.
    result["word_results"] = (patient.assessment_summary or {}).get("word_results", [])
    result["game_predictions"] = (patient.assessment_summary or {}).get("game_predictions")
    result["alphabet_completed"] = bool((patient.assessment_summary or {}).get("alphabet"))
    # severity_classification above comes from SessionModel, which only
    # ever reflects the single most-recently-analyzed WORD (see
    # assessment_lookup.py) -- override with the whole-session read
    # stored by POST /assessment/complete when we have one.
    session_severity = (patient.assessment_summary or {}).get("severity_classification")
    if session_severity:
        result["severity_classification"] = session_severity
    return result


@router.get("/me/game-plan")
async def get_my_game_plan(
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """The game-prediction agent's answer for this kid's latest assessment.
    Returns the stored prediction when there is one; for an assessment taken
    before this existed (word_results saved, no prediction), computes it now
    and saves it so the next read is instant. null when there is nothing to
    predict from yet."""
    summary = patient.assessment_summary or {}
    if summary.get("game_predictions"):
        return summary["game_predictions"]
    word_results = summary.get("word_results") or []
    if not word_results:
        return None
    prediction = await asyncio.to_thread(_predict_games, word_results, patient.first_name)
    if prediction is not None:
        patient.assessment_summary = {**summary, "game_predictions": prediction}
        db.add(patient)
        await db.commit()
    return prediction


# ------------------------------------------------------------------ #
#  Alphabet check -> VaakMirror parameters                             #
# ------------------------------------------------------------------ #

# Untouched VaakMirror round size (agent/round_size_heuristic.py:
# DEFAULT_ROUND_SIZE). A row still at this value means nobody, therapist or
# heuristic, has changed it, so the agent may set it; anything else is
# someone's deliberate choice and is left alone.
_UNTOUCHED_ROUND_SIZE = 10
_ROUND_SIZE_GAMES = (GameName.mirror_mirror, GameName.lip_sync_hero)


class AlphabetCompleteRequest(BaseModel):
    # One entry per letter the child said, as returned by
    # POST /assessment/alphabet/analyze. Only `letter`, `correct` and
    # `heard_as` are used; sound ids and groups come from the server catalog.
    letter_results: list[dict] = []


def _plan_alphabet(letter_results: list[dict]) -> dict:
    from app.graph.alphabet_graph import get_plan_graph
    return get_plan_graph().invoke({"letter_results": letter_results})["plan"]


@router.post("/alphabet/complete")
async def complete_alphabet(
    data: AlphabetCompleteRequest,
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """Runs the alphabet plan graph over the child's letter results, stores
    the plan, and applies its round size to VaakMirror's per-game settings
    (only where still at the default). VaakMirror's games then read the rest
    of the parameters from GET /vaakmirror/me/params."""
    from sqlalchemy import select

    letter_results = data.letter_results[:30]
    plan = await asyncio.to_thread(_plan_alphabet, letter_results)

    summary = dict(patient.assessment_summary or {})
    summary["alphabet"] = {
        "plan": plan,
        "letter_results": [
            {k: r.get(k) for k in ("letter", "word", "correct", "heard_as", "status")}
            for r in letter_results if isinstance(r, dict)
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    patient.assessment_summary = summary
    db.add(patient)

    params = plan["vaakmirror_params"]
    if plan["ready"]:
        for game in _ROUND_SIZE_GAMES:
            row = (await db.execute(
                select(VaakMirrorRoundSizeSetting).where(
                    VaakMirrorRoundSizeSetting.patient_id == str(patient.id),
                    VaakMirrorRoundSizeSetting.game == game,
                )
            )).scalar_one_or_none()
            if row is None:
                db.add(VaakMirrorRoundSizeSetting(
                    patient_id=str(patient.id), game=game, round_size=params["round_size"]))
            elif row.round_size == _UNTOUCHED_ROUND_SIZE:
                row.round_size = params["round_size"]
    await db.commit()
    return plan


@router.get("/me/alphabet")
async def get_my_alphabet(patient: BreathQuestPatient = Depends(get_current_patient)):
    """The stored alphabet plan (or null), for revisits."""
    return (patient.assessment_summary or {}).get("alphabet")
