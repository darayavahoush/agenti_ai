"""
Recent-window heuristic for suggesting a VaakMirror round size, mirroring
simple_difficulty_heuristic's raise/hold/lower pattern but driven by
Attempt.outcome accuracy instead of Chime's success/quit rates.

Note: unlike Chime, VaakMirror's AttemptOutcome has no "quit"/incomplete
state (passed/caught/missed only), so this is accuracy-only — no quit-rate
term. AttemptLabel (therapist correct/incorrect) is a sparse QA overlay,
not populated on every attempt, so it's intentionally NOT used here.
"""
from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vaakmirror_models import (
    Attempt, VaakMirrorSession, AttemptOutcome, GameName, VaakMirrorRoundSizeSetting,
)

WINDOW_SIZE = 20
MIN_ATTEMPTS = 6
RAISE_THRESHOLD = 0.85
LOWER_THRESHOLD = 0.50
STEP = 2
MIN_ROUND_SIZE = 4
MAX_ROUND_SIZE = 20
DEFAULT_ROUND_SIZE = 10

SUCCESS_OUTCOMES = {AttemptOutcome.passed, AttemptOutcome.caught}

Action = Literal["raise", "hold", "lower"]


@dataclass
class RoundSizeSuggestion:
    current: int
    suggested: int
    action: Action
    accuracy: Optional[float]
    n_attempts_considered: int
    reason: str


async def _recent_attempts(db: AsyncSession, patient_id: str, game: GameName, limit: int = WINDOW_SIZE):
    stmt = (
        select(Attempt)
        .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
        .where(
            VaakMirrorSession.patient_id == patient_id,
            VaakMirrorSession.game == game,
        )
        .order_by(Attempt.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_current_round_size(
    db: AsyncSession, patient_id: str, game: GameName
) -> VaakMirrorRoundSizeSetting:
    stmt = select(VaakMirrorRoundSizeSetting).where(
        VaakMirrorRoundSizeSetting.patient_id == patient_id,
        VaakMirrorRoundSizeSetting.game == game,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    setting = VaakMirrorRoundSizeSetting(patient_id=patient_id, game=game, round_size=DEFAULT_ROUND_SIZE)
    db.add(setting)
    await db.flush()
    return setting


async def suggest_round_size(db: AsyncSession, patient_id: str, game: GameName) -> RoundSizeSuggestion:
    setting = await get_current_round_size(db, patient_id, game)
    current = setting.round_size

    attempts = await _recent_attempts(db, patient_id, game)
    n = len(attempts)

    if n < MIN_ATTEMPTS:
        return RoundSizeSuggestion(
            current=current, suggested=current, action="hold", accuracy=None,
            n_attempts_considered=n,
            reason=f"fewer than {MIN_ATTEMPTS} recent attempts — holding steady until there's enough data",
        )

    successes = sum(1 for a in attempts if a.outcome in SUCCESS_OUTCOMES)
    accuracy = successes / n

    if accuracy >= RAISE_THRESHOLD and current < MAX_ROUND_SIZE:
        suggested, action = min(current + STEP, MAX_ROUND_SIZE), "raise"
        reason = f"accuracy {accuracy:.0%} over last {n} attempts is at/above {RAISE_THRESHOLD:.0%} — suggest raising round size"
    elif accuracy <= LOWER_THRESHOLD and current > MIN_ROUND_SIZE:
        suggested, action = max(current - STEP, MIN_ROUND_SIZE), "lower"
        reason = f"accuracy {accuracy:.0%} over last {n} attempts is at/below {LOWER_THRESHOLD:.0%} — suggest lowering round size"
    else:
        suggested, action = current, "hold"
        reason = f"accuracy {accuracy:.0%} over last {n} attempts is within the hold band — keeping round size steady"

    return RoundSizeSuggestion(
        current=current, suggested=suggested, action=action, accuracy=accuracy,
        n_attempts_considered=n, reason=reason,
    )
