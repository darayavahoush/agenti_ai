"""
routers/dashboard.py — Therapist dashboard: analytics, progress, notes.

Fixed 2026-08-11: was pointing at app.models.patient.Patient / app.models.session.Session
(Assessment's models) instead of BreathQuestPatient/GameSession/TherapistNote. Also fixed
two scoping bugs found during the rewrite: get_dashboard_summary queried ALL patients with
no therapist filter, and get_patient_progress had no ownership check (any therapist could
view any other therapist's patient by ID). Notes now use the real TherapistNote model
instead of 501/placeholder stubs.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient, GameSession, TherapistNote, LevelID
from app.schemas.breathquest_schemas import (
    PatientProgress, LevelProgress, DashboardSummary,
    PatientDetailOut, SessionOut,
    NoteCreate, NoteUpdate, NoteOut,
)
from app.breathquest_core.deps import get_current_therapist

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

LEVEL_NAMES = {
    "pinwheel":    "Pinwheel Spin",
    "float_rider": "Float Rider",
    "candle":      "Candle Gauntlet",
    "balloon":     "Balloon Pop",
    "dandelion":   "Dandelion Storm",
    "dragon":      "Dragon Fire",
}


async def _get_owned_patient(patient_id: str, therapist_id, db: AsyncSession) -> BreathQuestPatient:
    result = await db.execute(
        select(BreathQuestPatient).where(
            BreathQuestPatient.id == patient_id,
            BreathQuestPatient.therapist_id == therapist_id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


# ------------------------------------------------------------------ #
#  Summary                                                             #
# ------------------------------------------------------------------ #

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BreathQuestPatient).where(BreathQuestPatient.therapist_id == therapist.id)
    )
    patients = result.scalars().all()
    patient_ids = [p.id for p in patients]
    active_count = sum(1 for p in patients if p.is_active)

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    week_stats = await db.execute(
        select(
            func.count(GameSession.id).label("count"),
            func.avg(GameSession.avg_breath_strength).label("avg_accuracy"),
            func.avg(GameSession.stars_earned).label("avg_stars"),
        ).where(
            GameSession.patient_id.in_(patient_ids) if patient_ids else False,
            GameSession.started_at >= week_ago,
        )
    )
    week = week_stats.one()

    patient_details = []
    for p in patients:
        stats = await db.execute(
            select(
                func.count(GameSession.id).label("total"),
                func.sum(GameSession.stars_earned).label("stars"),
                func.max(GameSession.started_at).label("last"),
            ).where(GameSession.patient_id == p.id)
        )
        row = stats.one()
        patient_details.append(PatientDetailOut(
            id=str(p.id), first_name=p.first_name, avatar=p.avatar, age=p.age,
            is_active=p.is_active, created_at=p.created_at,
            diagnosis_notes=p.diagnosis_notes,
            total_sessions=row.total or 0, total_stars=int(row.stars or 0),
            last_session_at=row.last,
        ))

    return DashboardSummary(
        total_patients=len(patients),
        active_patients=active_count,
        sessions_this_week=week.count or 0,
        avg_stars_this_week=round(float(week.avg_stars), 2) if week.avg_stars else None,
        avg_accuracy_this_week=round(float(week.avg_accuracy), 2) if week.avg_accuracy else None,
        most_improved_patient=None,
        patients=patient_details,
    )


# ------------------------------------------------------------------ #
#  Patient progress                                                    #
# ------------------------------------------------------------------ #

@router.get("/patients/{patient_id}/progress", response_model=PatientProgress)
async def get_patient_progress(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_owned_patient(patient_id, therapist.id, db)

    result = await db.execute(
        select(GameSession)
        .where(GameSession.patient_id == patient.id)
        .order_by(GameSession.started_at.desc())
    )
    sessions = result.scalars().all()

    total_stars = sum(s.stars_earned or 0 for s in sessions)
    accuracy_vals_all = [s.avg_breath_strength for s in sessions if s.avg_breath_strength is not None]
    avg_accuracy = round(sum(accuracy_vals_all) / len(accuracy_vals_all), 2) if accuracy_vals_all else 0

    level_progress = []
    for level_id, level_name in LEVEL_NAMES.items():
        level_sessions = [s for s in sessions if s.level_id == level_id]
        if level_sessions:
            best_stars = max(s.stars_earned or 0 for s in level_sessions)
            avg_stars = sum(s.stars_earned or 0 for s in level_sessions) / len(level_sessions)
            accuracy_vals = [s.avg_breath_strength for s in level_sessions if s.avg_breath_strength is not None]
            avg_accuracy_level = sum(accuracy_vals) / len(accuracy_vals) if accuracy_vals else None
            last_played = max(s.started_at for s in level_sessions)
        else:
            best_stars = 0
            avg_stars = 0.0
            avg_accuracy_level = None
            last_played = None

        level_progress.append(LevelProgress(
            level_id=level_id,
            level_name=level_name,
            attempts=len(level_sessions),
            best_stars=best_stars,
            avg_stars=round(avg_stars, 2),
            avg_breath_strength=round(avg_accuracy_level, 2) if avg_accuracy_level else None,
            last_played=last_played,
        ))

    trend = None
    if len(sessions) >= 6:
        recent = [s.avg_breath_strength or 0 for s in sessions[:5]]
        older  = [s.avg_breath_strength or 0 for s in sessions[5:10]]
        trend = round((sum(recent) / len(recent)) - (sum(older) / len(older)), 2)

    return PatientProgress(
        patient_id=str(patient.id),
        first_name=patient.first_name,
        avatar=patient.avatar,
        total_sessions=len(sessions),
        total_stars=total_stars,
        max_possible_stars=len(LEVEL_NAMES) * 3,
        completion_rate=(sum(1 for s in sessions if s.completed) / len(sessions)) if sessions else 1.0,
        avg_breath_strength=avg_accuracy,
        improvement_trend=trend,
        level_progress=level_progress,
        recent_sessions=[SessionOut(
            id=str(s.id),
            patient_id=str(s.patient_id),
            level_id=s.level_id,
            started_at=s.started_at,
            ended_at=s.ended_at,
            duration_seconds=s.duration_seconds or 0.0,
            status=s.status,
            stars_earned=s.stars_earned or 0,
            completed=s.completed,
            avg_breath_strength=s.avg_breath_strength or 0,
            max_breath_strength=s.max_breath_strength or 0,
            breath_consistency=s.breath_consistency or 0.0,
            total_puffs=s.total_puffs or 0,
            lives_lost=s.lives_lost or 0,
        ) for s in sessions[:10]],
    )


# ------------------------------------------------------------------ #
#  Notes                                                               #
# ------------------------------------------------------------------ #

@router.post("/patients/{patient_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    patient_id: str,
    data: NoteCreate,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_patient(patient_id, therapist.id, db)

    note = TherapistNote(
        patient_id=patient_id,
        therapist_id=therapist.id,
        content=data.content,
    )
    db.add(note)
    await db.flush()
    return NoteOut(
        id=str(note.id), patient_id=str(note.patient_id), therapist_id=str(note.therapist_id),
        content=note.content, created_at=note.created_at, updated_at=note.updated_at,
    )


@router.get("/patients/{patient_id}/notes", response_model=list[NoteOut])
async def list_notes(
    patient_id: str,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_patient(patient_id, therapist.id, db)

    result = await db.execute(
        select(TherapistNote)
        .where(TherapistNote.patient_id == patient_id)
        .order_by(TherapistNote.created_at.desc())
    )
    notes = result.scalars().all()
    return [NoteOut(
        id=str(n.id), patient_id=str(n.patient_id), therapist_id=str(n.therapist_id),
        content=n.content, created_at=n.created_at, updated_at=n.updated_at,
    ) for n in notes]


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: str,
    data: NoteUpdate,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TherapistNote).where(
            TherapistNote.id == note_id,
            TherapistNote.therapist_id == therapist.id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    note.content = data.content
    note.updated_at = datetime.now(timezone.utc)
    return NoteOut(
        id=str(note.id), patient_id=str(note.patient_id), therapist_id=str(note.therapist_id),
        content=note.content, created_at=note.created_at, updated_at=note.updated_at,
    )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TherapistNote).where(
            TherapistNote.id == note_id,
            TherapistNote.therapist_id == therapist.id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
