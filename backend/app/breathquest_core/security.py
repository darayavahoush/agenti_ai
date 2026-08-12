from datetime import datetime, timedelta, timezone
from typing import Any
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.breathquest_core.config import get_breathquest_settings

settings = get_breathquest_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------ #
#  Password helpers (therapists)                                       #
# ------------------------------------------------------------------ #

def hash_password(password: str) -> str:
    """bcrypt via pwd_context (already imported, was previously only used
    as verify_password's fallback path). Salted SHA-256 has no adaptive
    work factor -- cheap to brute-force at scale, unlike bcrypt. Safe to
    switch without a migration: verify_password's existing salt.split('$')
    logic throws on a bcrypt hash (multiple '$' delimiters) and falls
    through to the pwd_context.verify() branch, so pre-existing SHA-256
    hashes keep verifying correctly and don't need rehashing."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    # Verify SHA-256 hashed password with salt
    try:
        salt, stored_hash = hashed.split('$')
        salted_password = plain + salt
        computed_hash = hashlib.sha256(salted_password.encode()).hexdigest()
        return computed_hash == stored_hash
    except:
        # Fallback to bcrypt for existing passwords
        try:
            return pwd_context.verify(plain, hashed)
        except:
            return False


# ------------------------------------------------------------------ #
#  JWT (therapists)                                                    #
# ------------------------------------------------------------------ #

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "therapist"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ------------------------------------------------------------------ #
#  PIN tokens (kids)                                                   #
# ------------------------------------------------------------------ #

def hash_pin(pin: str) -> str:
    """Store PINs as SHA-256 (not bcrypt — PINs are short and already validated)."""
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(plain: str, hashed: str) -> bool:
    return hash_pin(plain) == hashed


def create_kid_token(patient_id: str) -> str:
    """Long-lived simple token for kid sessions."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.KID_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(patient_id), "exp": expire, "type": "patient"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_kid_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "patient":
            return None
        return payload
    except JWTError:
        return None


# ------------------------------------------------------------------ #
#  JWT (parents)                                                       #
# ------------------------------------------------------------------ #

def create_parent_token(parent_id: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(parent_id), "exp": expire, "type": "parent"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_parent_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "parent":
            return None
        return payload
    except JWTError:
        return None


def generate_invite_code() -> str:
    """Short, unambiguous (no 0/O/1/I) code for a therapist to hand a parent."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


async def generate_unique_player_code(db, avatar: str) -> str:
    """Collision-checked player code generator, shared by kid self-registration
    and therapist-driven patient creation. Ported from quest-games' inline
    version in auth.py, retargeted at BreathQuestPatient (agenti_ai's model)
    instead of quest-games' own Patient."""
    import random
    from sqlalchemy import select
    from app.models.breathquest_models import BreathQuestPatient

    while True:
        code = avatar.upper()[:5] + str(random.randint(10, 99))
        exists = await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.player_code == code))
        if not exists.scalar_one_or_none():
            return code
