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


@router.get("")
async def get_my_profile(
    patient: BreathQuestPatient = Depends(get_current_patient),
):
    """Kid-authenticated 'refresh my own state' lookup.

    get_current_patient re-queries the DB fresh on every request (see
    breathquest_core/deps.py), so this always reflects the live row --
    unlike AuthContext's cached bq_user_data in localStorage, which is
    only ever written at explicit login/register/markAssessmentComplete
    time. Without this endpoint, a kid whose assessment_completed flips
    to true through a *different* session (a therapist-supervised
    session on another device, a manual DB fix, etc.) keeps seeing a
    stale "locked" state on their own device indefinitely, since nothing
    else ever re-fetches this after initial hydration from localStorage.
    Call this once on app load (see AuthContext.jsx) and reconcile the
    cached patient object with it.
    """
    return {
        "patient_id": str(patient.id),
        "first_name": patient.first_name,
        "avatar": patient.avatar,
        "avatar_photo_url": patient.avatar_photo_url,
        "player_code": patient.player_code,
        "assessment_completed": patient.assessment_completed,
    }


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
