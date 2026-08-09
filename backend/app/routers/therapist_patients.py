"""
routers/therapist_patients.py -- Therapist-scoped patient list.

Replaces the retired, unauthenticated GET /patients/ in main.py (see its
2026-08-07 disable comments) with one scoped via Patient.registered_therapist_id.
Deliberately does NOT touch GET /assessment/patients (service-key protected,
for service-to-service calls, not browser JS).

Patient creation doesn't set registered_therapist_id anywhere yet (no live
POST /patients endpoint exists at all right now -- a separate, flagged gap),
so this correctly returns an empty list until that's built.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.patient import Patient
from app.models.therapist import Therapist
from app.deps.therapist_auth_deps import get_current_therapist

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("")
async def list_my_patients(
    therapist: Therapist = Depends(get_current_therapist),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Patient).where(Patient.registered_therapist_id == therapist.id)
    )
    patients = result.scalars().all()
    return [
        {"id": str(p.id), "name": p.name, "age": p.age, "diagnosis": p.diagnosis}
        for p in patients
    ]
