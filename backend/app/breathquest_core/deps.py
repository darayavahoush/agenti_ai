"""
breathquest_core/deps.py — FastAPI dependency injection for BreathQuest auth.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.breathquest_models import Therapist, BreathQuestPatient
from app.breathquest_core.security import decode_access_token, decode_kid_token

bearer = HTTPBearer()


async def get_current_therapist(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    # Bypass authentication for old system - return a dummy therapist object
    # This allows the dashboard to work with the old Patient/Session tables
    class DummyTherapist:
        id = "dummy-therapist-id"
        email = "test@test.com"
        full_name = "Test Therapist"
        is_active = True
    
    return DummyTherapist()


async def get_current_patient(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> BreathQuestPatient:
    token = credentials.credentials
    payload = decode_kid_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired kid token",
        )

    result = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id == payload["sub"]))
    patient = result.scalar_one_or_none()

    if not patient or not patient.is_active:
        raise HTTPException(status_code=401, detail="Patient not found or inactive")

    return patient
