from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.vaakmirror_auth import assert_therapist_owns_patient, get_current_therapist_id
from app.database import get_db
from app.models.vaakmirror_models import Attempt, AttemptLabel, VaakMirrorSession
from app.schemas.vaakmirror_schemas import AttemptOut

router = APIRouter(tags=["vaakmirror-labeling"])


@router.get("/patients/{patient_id}/attempts", response_model=list[AttemptOut])
async def list_patient_attempts(
    patient_id: str,
    unlabeled_only: bool = False,
    limit: int = 30,
    therapist_id: str = Depends(get_current_therapist_id),
    db: AsyncSession = Depends(get_db),
):
    await assert_therapist_owns_patient(db, therapist_id, patient_id)

    stmt = (
        select(Attempt)
        .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
        .where(VaakMirrorSession.patient_id == patient_id)
        .where(Attempt.shape.is_not(None))
    )
    if unlabeled_only:
        stmt = stmt.where(Attempt.therapist_label.is_(None))
    stmt = stmt.order_by(Attempt.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


class LabelIn(BaseModel):
    label: AttemptLabel


@router.post("/attempts/{attempt_id}/label", response_model=AttemptOut)
async def label_attempt(
    attempt_id: int,
    body: LabelIn,
    therapist_id: str = Depends(get_current_therapist_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Attempt, VaakMirrorSession.patient_id)
        .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
        .where(Attempt.id == attempt_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Attempt not found")
    attempt, patient_id = row

    await assert_therapist_owns_patient(db, therapist_id, patient_id)

    attempt.therapist_label = body.label
    attempt.labeled_at = datetime.now(timezone.utc)
    attempt.labeled_by = therapist_id
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    return attempt
