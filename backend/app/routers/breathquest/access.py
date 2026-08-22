"""
routers/breathquest/access.py — kid-authenticated entitlement check.

GET /me/access lets the frontend (ProtectedKid in App.jsx) find out, for
the currently logged-in kid, whether their linked parent/therapist has an
active subscription -- before letting them into a gameplay route. Uses
breathquest_core/entitlements.py's shared resolution logic, the same
logic real game routers would depend on if/when they add server-side
gating too (not done yet -- this endpoint is the enforcement surface for
now, called from the frontend rather than baked into every game route).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.breathquest_models import BreathQuestPatient
from app.breathquest_core.deps import get_current_patient
from app.breathquest_core.entitlements import get_patient_entitlement

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/access")
async def get_my_access(
    patient: BreathQuestPatient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    status = await get_patient_entitlement(patient, db)
    return {
        "has_access": status.has_access,
        "reason": status.reason,
        "trial_ends_at": status.trial_ends_at,
        "plan_type": status.plan_type,
    }
