from datetime import datetime, timedelta, timezone
from typing import Any
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


# ------------------------------------------------------------------ #
#  Refresh tokens (all owner kinds)                                    #
# ------------------------------------------------------------------ #
#
# Opaque random strings, not JWTs -- unlike access tokens, these need to be
# revocable (POST /auth/logout) and individually look-up-able (POST
# /auth/refresh), which means a DB round-trip is unavoidable and there's no
# benefit to a signed/structured token here. Raw value is returned to the
# client exactly once; only its SHA-256 hash is ever stored, matching
# RefreshToken's own docstring reasoning in breathquest_models.py.

REFRESH_TOKEN_EXPIRE_DAYS = {
    "therapist": 14,
    "parent": 14,
    "patient": 30,  # matches the old KID_TOKEN_EXPIRE_DAYS window, moved to the revocable side
}


def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_refresh_token(db: AsyncSession, owner_kind: str, owner_id: str) -> str:
    """Generates a new refresh token, stores its hash, and returns the raw
    value for the caller to send to the client. Caller is responsible for
    the actual db.commit() -- matches login_throttle.py's existing
    stage-here-commit-at-call-site pattern in this codebase."""
    import uuid
    from app.models.breathquest_models import RefreshToken  # local import avoids a circular import with breathquest_models -> security at module load time

    raw_token = secrets.token_urlsafe(48)
    expire_days = REFRESH_TOKEN_EXPIRE_DAYS.get(owner_kind, 14)
    owner_uuid = uuid.UUID(owner_id) if isinstance(owner_id, str) else owner_id
    token = RefreshToken(
        token_hash=_hash_refresh_token(raw_token),
        owner_kind=owner_kind,
        owner_id=owner_uuid,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expire_days),
    )
    db.add(token)
    await db.flush()
    return raw_token


REFRESH_TOKEN_REUSE_GRACE_SECONDS = 15
# /auth/refresh hard-revokes the old refresh token the instant a new one is
# issued (see refresh_access_token). That's correct in general (rotation is
# what makes a leaked-then-used token only good for one use), but it has a
# real failure mode: two tabs/devices sharing one login can both have access
# tokens expire around the same moment, both hit a 401, and both race into
# _attemptSilentRefresh() independently -- the frontend's in-flight dedup
# only covers one browser tab's JS memory, not other tabs or devices. The
# loser of that race gets a real 401 from a token that WAS valid a moment
# ago, and the frontend interceptor treats any refresh failure as a dead
# session: it wipes localStorage and hard-redirects to login, for everyone,
# even though the account's session was completely fine seconds earlier.
# A short grace window on a *just*-revoked token absorbs that race without
# reopening the actual security case rotation exists for (a token revoked
# more than ~15s ago, or one that's ever been used to complete a full
# rotation once already via this grace path, still fails as it should).


async def get_valid_refresh_token(db: AsyncSession, raw_token: str, allow_recent_reuse: bool = False):
    """Returns the RefreshToken row if raw_token hashes to a stored,
    unrevoked (or revoked within the reuse grace window, if allowed),
    unexpired token -- else None. Caller decides what to do with None (401
    for /refresh, treat /logout as already-logged-out).

    allow_recent_reuse=True is for the /auth/refresh path only -- see
    REFRESH_TOKEN_REUSE_GRACE_SECONDS above. Logout intentionally never
    passes this: an explicit logout should be an immediate, unambiguous
    revoke regardless of any in-flight race elsewhere."""
    from app.models.breathquest_models import RefreshToken

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_refresh_token(raw_token))
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None
    if token.revoked_at is not None:
        within_grace = (
            allow_recent_reuse
            and (datetime.now(timezone.utc) - token.revoked_at).total_seconds() <= REFRESH_TOKEN_REUSE_GRACE_SECONDS
        )
        if not within_grace:
            return None
    if token.expires_at <= datetime.now(timezone.utc):
        return None
    return token


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """POST /auth/logout's core action. No-ops silently on an already-
    revoked/expired/unknown token -- logging out twice, or logging out
    with a stale token, isn't an error from the client's perspective."""
    token = await get_valid_refresh_token(db, raw_token)
    if token is not None:
        token.revoked_at = datetime.now(timezone.utc)
        await db.flush()


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
