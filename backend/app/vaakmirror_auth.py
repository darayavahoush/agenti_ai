from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

bearer = HTTPBearer()


def _decode(token: str) -> dict:
    try:
        # Pydantic settings attributes are uppercase or lowercase depending on settings definition.
        # We will support both Settings.SECRET_KEY / settings.SECRET_KEY.
        # Let's read from the main settings class: settings.SECRET_KEY and settings.ALGORITHM.
        secret_key = getattr(settings, "SECRET_KEY", "supersecretkey")
        algorithm = getattr(settings, "ALGORITHM", "HS256")
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def _check_active(db: AsyncSession, table: str, row_id: str) -> bool:
    result = await db.execute(text(f"SELECT is_active FROM {table} WHERE id = :id"), {"id": row_id})
    row = result.first()
    return bool(row and row.is_active)


async def get_current_therapist_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> str:
    payload = _decode(credentials.credentials)
    if payload.get("type") != "therapist":
        raise HTTPException(status_code=401, detail="A therapist token is required here")
    therapist_id = payload.get("sub")
    if not therapist_id or not await _check_active(db, "breathquest_therapists", therapist_id):
        raise HTTPException(status_code=401, detail="Therapist not found or inactive")
    return therapist_id


async def get_current_patient_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> str:
    payload = _decode(credentials.credentials)
    if payload.get("type") != "patient":
        raise HTTPException(status_code=401, detail="A patient token is required here")
    patient_id = payload.get("sub")
    if not patient_id or not await _check_active(db, "breathquest_patients", patient_id):
        raise HTTPException(status_code=401, detail="Patient not found or inactive")
    return patient_id


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> tuple[str, str]:
    payload = _decode(credentials.credentials)
    kind = payload.get("type")
    sub = payload.get("sub")
    if kind not in ("therapist", "patient") or not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    table = "breathquest_therapists" if kind == "therapist" else "breathquest_patients"
    if not await _check_active(db, table, sub):
        raise HTTPException(status_code=401, detail=f"{kind.title()} not found or inactive")
    return kind, sub


async def assert_therapist_owns_patient(db: AsyncSession, therapist_id: str, patient_id: str) -> None:
    result = await db.execute(text("SELECT therapist_id FROM breathquest_patients WHERE id = :id"), {"id": patient_id})
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    if row.therapist_id is not None and str(row.therapist_id) != therapist_id:
        raise HTTPException(status_code=403, detail="This patient belongs to a different therapist")


async def get_patient_summary(db: AsyncSession, patient_id: str) -> dict | None:
    result = await db.execute(
        text("SELECT id, first_name, age FROM breathquest_patients WHERE id = :id"), {"id": patient_id}
    )
    row = result.first()
    return {"id": str(row.id), "first_name": row.first_name, "age": row.age} if row else None
