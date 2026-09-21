"""
app/breathquest_core/username.py -- editable, memorable @usernames for kids,
parents and therapists.

Why this exists: player_code is auto-generated (avatar prefix + 2 digits) and
only unique inside breathquest_patients. Usernames are the human-chosen
counterpart -- Instagram-style, changeable any time -- and are unique across
ALL THREE account tables at once, so "@sunny.otter" can only ever belong to
one person in the whole app regardless of role.

Rules (deliberately close to Instagram's, tightened for a children's app):
  * 3-20 characters
  * lowercase letters, digits, "_" and "." only (input is lower-cased for you,
    so "Sunny_Otter" and "sunny_otter" are the same handle)
  * at least one letter (no all-digit handles that read like phone numbers)
  * "." can't start or end a handle and can't repeat ("..")
  * not a reserved/system word
  * can't equal anyone's player_code (kid-login accepts either one, so the two
    namespaces must never overlap or one code could hit two accounts)

Uniqueness is enforced two ways: a UNIQUE index per table (last line of
defence against a race inside one table) plus is_username_taken() below, which
checks all three tables. The one gap -- two different roles claiming the same
name in the same instant -- is a tiny window; set_username() re-checks right
before the write and turns any IntegrityError into a clean 409.
"""

from __future__ import annotations

import random
import re
import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breathquest_models import BreathQuestPatient, Parent
from app.models.therapist import Therapist

USERNAME_MIN = 3
USERNAME_MAX = 20

_ALLOWED = re.compile(r"^[a-z0-9._]+$")

# Words that would look official or confusing as a handle. Kept short and
# obvious on purpose -- easy to extend.
RESERVED = frozenset({
    "admin", "administrator", "root", "system", "support", "help", "staff",
    "moderator", "mod", "official", "agenti", "agentiai", "agenti_ai",
    "anthropic", "claude", "therapist", "teacher", "parent", "kid", "child",
    "player", "null", "none", "undefined", "me", "you", "user", "username",
    "api", "www", "login", "logout", "register", "signup", "settings",
    "breathquest", "vaakmirror", "test", "guest",
})


def normalize_username(raw: str | None) -> str:
    """Trim, drop a leading '@' (people type it out of habit), lower-case."""
    return (raw or "").strip().lstrip("@").strip().lower()


def validate_username_format(raw: str | None) -> tuple[str | None, str | None]:
    """Returns (normalized, error). error is a short, kid-readable sentence or
    None when the format is fine. Does NOT touch the database."""
    name = normalize_username(raw)

    if not name:
        return name, "Pick a username to continue."
    if len(name) < USERNAME_MIN:
        return name, f"Too short -- use at least {USERNAME_MIN} characters."
    if len(name) > USERNAME_MAX:
        return name, f"Too long -- use {USERNAME_MAX} characters or fewer."
    if not _ALLOWED.match(name):
        return name, "Only letters, numbers, dots (.) and underscores (_) are allowed -- no spaces."
    if not re.search(r"[a-z]", name):
        return name, "Add at least one letter."
    if name.startswith(".") or name.endswith("."):
        return name, "A username can't start or end with a dot."
    if ".." in name:
        return name, "No two dots in a row."
    if name in RESERVED:
        return name, "That name is reserved -- try something else."
    return name, None


@dataclass
class UsernameCheck:
    username: str
    available: bool
    reason: str | None = None  # populated whenever available is False


async def is_username_taken(
    db: AsyncSession,
    username: str,
    *,
    exclude_kind: str | None = None,
    exclude_id: uuid.UUID | str | None = None,
) -> bool:
    """True if `username` (already normalized) belongs to any account other
    than the one identified by (exclude_kind, exclude_id) -- so re-saving your
    own current handle isn't reported as a clash. Also True if it equals any
    kid's player_code (see module docstring)."""
    checks = (
        ("patient", BreathQuestPatient, BreathQuestPatient.username),
        ("parent", Parent, Parent.username),
        ("therapist", Therapist, Therapist.username),
    )
    for kind, model, col in checks:
        q = select(model.id).where(col == username)
        if exclude_kind == kind and exclude_id is not None:
            q = q.where(model.id != exclude_id)
        if (await db.execute(q.limit(1))).first():
            return True

    code_hit = await db.execute(
        select(BreathQuestPatient.id)
        .where(func.lower(BreathQuestPatient.player_code) == username)
        .limit(1)
    )
    return code_hit.first() is not None


async def check_username(
    db: AsyncSession,
    raw: str | None,
    *,
    exclude_kind: str | None = None,
    exclude_id: uuid.UUID | str | None = None,
) -> UsernameCheck:
    name, error = validate_username_format(raw)
    if error:
        return UsernameCheck(username=name or "", available=False, reason=error)
    if await is_username_taken(db, name, exclude_kind=exclude_kind, exclude_id=exclude_id):
        return UsernameCheck(username=name, available=False, reason="Someone already has that one -- try another.")
    return UsernameCheck(username=name, available=True)


async def set_username(
    db: AsyncSession,
    account,
    kind: str,
    raw: str | None,
) -> str:
    """Validates, checks cross-table uniqueness, writes and commits.
    `account` is the BreathQuestPatient / Parent / Therapist row; `kind` is
    "patient" | "parent" | "therapist". Raises HTTPException(422) for a bad
    format and HTTPException(409) for a taken name. Returns the saved handle."""
    result = await check_username(db, raw, exclude_kind=kind, exclude_id=account.id)
    if not result.available:
        # 409 for "taken", 422 for "doesn't fit the rules" -- lets the client
        # tell them apart if it ever wants to.
        _, fmt_error = validate_username_format(raw)
        raise HTTPException(status_code=422 if fmt_error else 409, detail=result.reason)

    account.username = result.username
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Someone already has that one -- try another.")
    return result.username


# ------------------------------------------------------------------ #
#  Suggestions (for the picker's one-tap chips)                       #
# ------------------------------------------------------------------ #

_ADJECTIVES = [
    "sunny", "brave", "happy", "swift", "cosmic", "jolly", "mighty", "sparkly",
    "gentle", "clever", "lucky", "bouncy", "cheery", "plucky", "zippy", "snowy",
]
_ANIMALS = [
    "otter", "panda", "fox", "owl", "koala", "tiger", "dolphin", "bunny",
    "penguin", "turtle", "falcon", "lion", "chick", "whale", "gecko", "robin",
]


def _clean_seed(seed: str | None) -> str:
    """Reduce a first name / avatar to something usable inside a handle."""
    s = re.sub(r"[^a-z0-9]", "", (seed or "").lower())
    return s[:10]


async def suggest_usernames(
    db: AsyncSession,
    *,
    seed: str | None = None,
    count: int = 4,
    exclude_kind: str | None = None,
    exclude_id: uuid.UUID | str | None = None,
) -> list[str]:
    """Up to `count` currently-available, format-valid handles. Playful
    adjective_animal combos, plus a seed-based one when a seed is given.
    Deliberately does NOT build handles from a kid's real first name -- a
    child's name is personal, and the point of a username is being something
    they chose, not something we derived from their identity."""
    rng = random.Random()
    candidates: list[str] = []

    animal_seed = _clean_seed(seed)
    if animal_seed and animal_seed in _ANIMALS:
        # `seed` is the avatar species when the caller passes it -- lean into it.
        candidates.append(f"{rng.choice(_ADJECTIVES)}_{animal_seed}{rng.randint(1, 99)}")

    tries = 0
    while len(candidates) < count * 4 and tries < 200:
        tries += 1
        joiner = rng.choice(["_", ".", ""])
        candidates.append(f"{rng.choice(_ADJECTIVES)}{joiner}{rng.choice(_ANIMALS)}{rng.choice(['', str(rng.randint(1, 99))])}")

    picked: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        _, err = validate_username_format(c)
        if err:
            continue
        if await is_username_taken(db, c, exclude_kind=exclude_kind, exclude_id=exclude_id):
            continue
        picked.append(c)
        if len(picked) >= count:
            break
    return picked
