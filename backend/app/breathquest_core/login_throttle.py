"""
breathquest_core/login_throttle.py — brute-force protection for
POST /auth/kid-login.

Kid accounts authenticate with a 4-digit PIN (10,000 possible values)
against a publicly-guessable identifier (first name or player code) --
with no rate limiting, an attacker can exhaust the full PIN space in
seconds. This module tracks failed attempts per identifier and applies
exponential backoff lockouts, without ever needing to know whether the
identifier resolves to a real patient.

Lockout schedule (failed_attempts -> lock duration once that count is
hit): 5 -> 30s, 8 -> 5min, 12 -> 30min, 15+ -> 2hr. Deliberately mild at
the low end -- a kid fat-fingering their own PIN a few times shouldn't
get locked out, but sustained guessing escalates fast.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import KidLoginThrottle

_LOCKOUT_SCHEDULE = (
    (15, timedelta(hours=2)),
    (12, timedelta(minutes=30)),
    (8, timedelta(minutes=5)),
    (5, timedelta(seconds=30)),
)


@dataclass
class ThrottleStatus:
    locked: bool
    retry_after_seconds: int | None = None


def _lockout_for(failed_attempts: int) -> timedelta | None:
    for threshold, duration in _LOCKOUT_SCHEDULE:
        if failed_attempts >= threshold:
            return duration
    return None


async def check_throttle(identifier: str, db: AsyncSession) -> ThrottleStatus:
    """Call before verifying a PIN. Does not record anything -- read-only
    check of whatever lockout a prior call to record_failure set."""
    normalized = identifier.strip().lower()
    result = await db.execute(
        select(KidLoginThrottle).where(KidLoginThrottle.identifier == normalized)
    )
    row = result.scalar_one_or_none()
    if row is None or row.locked_until is None:
        return ThrottleStatus(locked=False)

    now = datetime.now(timezone.utc)
    if row.locked_until <= now:
        return ThrottleStatus(locked=False)

    return ThrottleStatus(locked=True, retry_after_seconds=int((row.locked_until - now).total_seconds()))


async def record_failure(identifier: str, db: AsyncSession) -> None:
    """Call after a failed PIN check (wrong PIN, or no matching account).
    Increments the counter and sets/extends locked_until per the
    schedule. Caller is responsible for the actual db.commit() -- this
    only stages the change, matching kid_login's existing commit point."""
    normalized = identifier.strip().lower()
    result = await db.execute(
        select(KidLoginThrottle).where(KidLoginThrottle.identifier == normalized)
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if row is None:
        row = KidLoginThrottle(identifier=normalized, failed_attempts=0, first_failed_at=now)
        db.add(row)

    row.failed_attempts += 1
    row.last_failed_at = now
    lockout = _lockout_for(row.failed_attempts)
    row.locked_until = now + lockout if lockout is not None else row.locked_until


async def record_success(identifier: str, db: AsyncSession) -> None:
    """Call after a successful login. Clears the throttle row entirely --
    a legitimate login is the strongest possible signal the account
    isn't currently under attack, and resetting avoids a kid who
    mistyped their PIN a few times staying flagged after they get it
    right."""
    normalized = identifier.strip().lower()
    result = await db.execute(
        select(KidLoginThrottle).where(KidLoginThrottle.identifier == normalized)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
