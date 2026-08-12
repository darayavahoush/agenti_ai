"""
app/breathquest_core/deps.py — FastAPI dependency injection for auth.

Ported from quest-games' core/deps.py as part of the 2026-08-11 agenti_ai
<-> quest-games merge (see app/models/therapist.py's docstring). Decodes
against agenti_ai's canonical Therapist/Patient models (app/models/), not
quest-games' retiring ones (models/models.py there) -- this is the piece
that was missing on this side before the merge: agenti_ai's
therapist_auth.py could issue tokens (create_access_token) but nothing
here decoded one back into a real Therapist/Patient for route protection.

get_current_parent was added 2026-08-12 once Parent/Subscription models
and create_parent_token/decode_parent_token were ported over as part of
the same merge.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.therapist import Therapist
from app.models.breathquest_models import BreathQuestPatient, Parent
from app.breathquest_core.security import decode_access_token, decode_kid_token, decode_parent_token

bearer = HTTPBearer()


async def get_current_therapist(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Therapist:
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload or payload.get("type") != "therapist":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(Therapist).where(Therapist.id == payload["sub"]))
    therapist = result.scalar_one_or_none()

    if not therapist or not therapist.is_active:
        raise HTTPException(status_code=401, detail="Therapist not found or inactive")

    return therapist


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


async def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Parent:
    token = credentials.credentials
    payload = decode_parent_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired parent token",
        )

    result = await db.execute(select(Parent).where(Parent.id == payload["sub"]))
    parent = result.scalar_one_or_none()

    if not parent or not parent.is_active:
        raise HTTPException(status_code=401, detail="Parent not found or inactive")

    return parent
