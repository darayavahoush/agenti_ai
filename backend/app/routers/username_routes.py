"""
routers/username_routes.py -- the four username endpoints, built once and
mounted under each role's own router so kids, parents and therapists all get
identical behaviour:

    GET    <base>            -> {"username": "sunny.otter" | null}
    GET    <base>/check?username=x   -> {"username": "x", "available": bool, "reason": str|null}
    GET    <base>/suggestions        -> {"suggestions": [...]}
    PATCH  <base>            body {"username": "x"} -> {"username": "x"}

Mounted at (see the include_router calls next to each role's router):
    kid        /api/v1/breathquest/patients/me/username
    parent     /api/v1/parent/username
    therapist  /api/v1/auth/therapist/username

Every route is authenticated as the account it's about, on purpose: an open
"is this name taken?" endpoint would let anyone enumerate accounts, and the
shared IP rate limiter (20/min across all auth routes) is far too tight for a
live-as-you-type check. Because the caller is known, "available" also treats
the caller's own current handle as available, so re-saving it isn't an error.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.breathquest_core.username import check_username, set_username, suggest_usernames
from app.schemas.breathquest_schemas import (
    UsernameSetRequest, UsernameOut, UsernameCheckOut, UsernameSuggestionsOut,
)


def make_username_router(get_account, kind: str, seed_attr: str | None = None) -> APIRouter:
    """get_account: the FastAPI dependency that resolves the signed-in row
    (get_current_patient / get_current_parent / get_current_therapist).
    kind: "patient" | "parent" | "therapist" (used for the cross-table
    uniqueness check's self-exclusion). seed_attr: optional attribute on the
    account used to flavour suggestions (kids pass "avatar")."""
    router = APIRouter()

    @router.get("", response_model=UsernameOut)
    async def get_my_username(account=Depends(get_account)):
        return UsernameOut(username=account.username)

    @router.get("/check", response_model=UsernameCheckOut)
    async def check_my_username(
        username: str = Query(..., max_length=64),
        account=Depends(get_account),
        db: AsyncSession = Depends(get_db),
    ):
        result = await check_username(db, username, exclude_kind=kind, exclude_id=account.id)
        return UsernameCheckOut(username=result.username, available=result.available, reason=result.reason)

    @router.get("/suggestions", response_model=UsernameSuggestionsOut)
    async def my_username_suggestions(
        account=Depends(get_account),
        db: AsyncSession = Depends(get_db),
    ):
        seed = getattr(account, seed_attr, None) if seed_attr else None
        names = await suggest_usernames(db, seed=seed, exclude_kind=kind, exclude_id=account.id)
        return UsernameSuggestionsOut(suggestions=names)

    @router.patch("", response_model=UsernameOut)
    async def set_my_username(
        data: UsernameSetRequest,
        account=Depends(get_account),
        db: AsyncSession = Depends(get_db),
    ):
        saved = await set_username(db, account, kind, data.username)
        return UsernameOut(username=saved)

    return router
