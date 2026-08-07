"""
Auth dependency for the new Assessment-native Therapist accounts (see
app/models/therapist.py). Separate from app/vaakmirror_auth.py's
get_current_therapist_id, which checks the retiring breathquest_therapists
table -- this checks therapists instead. JWT signing/verification is reused
as-is from app.breathquest_core.security: both config sources share the
same SECRET_KEY/ALGORITHM defaults (confirmed no .env override), so tokens
are interchangeable at the crypto level -- only which table is_active gets
checked against differs.
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.breathquest_core.security import decode_access_token
from app.models.therapist import Therapist

bearer = HTTPBearer()


async def get_current_therapist(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Therapist:
    payload = decode_access_token(credentials.credentials)
    if not payload or payload.get("type") != "therapist":
        raise HTTPException(status_code=401, detail="A therapist token is required here")
    therapist_id = payload.get("sub")
    if not therapist_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(Therapist).where(Therapist.id == therapist_id))
    therapist = result.scalar_one_or_none()
    if not therapist or not therapist.is_active:
        raise HTTPException(status_code=401, detail="Therapist not found or inactive")
    return therapist
