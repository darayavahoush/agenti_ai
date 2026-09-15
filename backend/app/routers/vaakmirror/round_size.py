from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vaakmirror_models import GameName
from agent.round_size_heuristic import (
    get_current_round_size, suggest_round_size, MIN_ROUND_SIZE, MAX_ROUND_SIZE,
)

router = APIRouter(tags=["vaakmirror-round-size"])


class RoundSizeOut(BaseModel):
    patient_id: str
    game: GameName
    round_size: int


class RoundSizeSuggestionOut(BaseModel):
    current: int
    suggested: int
    action: str
    accuracy: Optional[float]
    n_attempts_considered: int
    reason: str


class RoundSizeSetIn(BaseModel):
    round_size: Optional[int] = Field(default=None, ge=MIN_ROUND_SIZE, le=MAX_ROUND_SIZE)
    apply_suggestion: bool = False


@router.get("/{patient_id}/{game}/round-size", response_model=RoundSizeOut)
async def get_round_size(patient_id: str, game: GameName, db: AsyncSession = Depends(get_db)):
    setting = await get_current_round_size(db, patient_id, game)
    await db.commit()
    return RoundSizeOut(patient_id=patient_id, game=game, round_size=setting.round_size)


@router.get("/{patient_id}/{game}/round-size/suggestion", response_model=RoundSizeSuggestionOut)
async def get_round_size_suggestion(patient_id: str, game: GameName, db: AsyncSession = Depends(get_db)):
    suggestion = await suggest_round_size(db, patient_id, game)
    await db.rollback()
    return RoundSizeSuggestionOut(**suggestion.__dict__)


@router.post("/{patient_id}/{game}/round-size", response_model=RoundSizeOut)
async def set_round_size(
    patient_id: str, game: GameName, body: RoundSizeSetIn, db: AsyncSession = Depends(get_db)
):
    if body.apply_suggestion:
        suggestion = await suggest_round_size(db, patient_id, game)
        new_size = suggestion.suggested
    elif body.round_size is not None:
        new_size = body.round_size
    else:
        raise HTTPException(400, "Provide either round_size or apply_suggestion=true")

    setting = await get_current_round_size(db, patient_id, game)
    setting.round_size = new_size
    await db.commit()
    await db.refresh(setting)
    return RoundSizeOut(patient_id=patient_id, game=game, round_size=setting.round_size)
