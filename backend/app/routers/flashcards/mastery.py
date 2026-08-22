"""
routers/flashcards/mastery.py — Persists per-attempt phoneme results and
maintains the PhonemeMastery aggregate other code should read.

record_attempt() is called from router.py's /evaluate right after
build_attempt_result() produces an AttemptResult. get_weak_phonemes() /
get_mastery_summary() are plain async functions other games (or
in-backend agent logic, e.g. breath_agent.py) can import directly and
call with their own `db` session + `patient_id` -- no HTTP round-trip
needed since everything lives in the same backend process (see
kid_progress.py's chime_data_store usage for the existing precedent of
one router reading another feature's data directly).
"""

import uuid
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcards_models import FlashcardAttempt, PhonemeMastery
from .schema import AttemptResult


async def record_attempt(
    db: AsyncSession,
    patient_id: uuid.UUID,
    result: AttemptResult,
    theme_id: str | None = None,
) -> None:
    """Writes the raw attempt log row, then upserts PhonemeMastery for
    every phoneme in this attempt. Commits once at the end. Called inline
    from /evaluate AFTER the response body already exists -- router.py
    wraps this call in try/except so a DB hiccup here can never cost the
    kid their already-computed result."""

    db.add(FlashcardAttempt(
        patient_id=patient_id,
        session_id=result.session_id,
        theme_id=theme_id,
        target_word=result.target_word,
        character=result.character,
        language="english",
        transcript=result.transcript,
        phoneme_matches=[m.model_dump() for m in result.phoneme_scores.matches],
        accuracy=result.phoneme_scores.accuracy,
        composite_score=result.composite_score,
        attempt_number=result.attempt_number,
        repeat_needed=result.repeat_needed,
    ))

    for match in result.phoneme_scores.matches:
        phoneme = match.expected.upper()
        existing = (await db.execute(
            select(PhonemeMastery).where(
                PhonemeMastery.patient_id == patient_id,
                PhonemeMastery.phoneme == phoneme,
            )
        )).scalar_one_or_none()

        if existing is None:
            existing = PhonemeMastery(patient_id=patient_id, phoneme=phoneme)
            db.add(existing)

        existing.attempts_count += 1
        if match.correct:
            existing.correct_count += 1
        existing.accuracy = round(existing.correct_count / existing.attempts_count * 100, 2)
        existing.last_word = result.target_word

    await db.commit()


async def get_mastery_summary(db: AsyncSession, patient_id: uuid.UUID) -> Dict[str, dict]:
    """Every phoneme this child has attempted at least once, keyed by
    phoneme, e.g. {"R": {"accuracy": 62.5, "attempts": 8, ...}, ...}.
    This is the shape other games / agent logic should consume."""
    rows = (await db.execute(
        select(PhonemeMastery).where(PhonemeMastery.patient_id == patient_id)
    )).scalars().all()
    return {
        r.phoneme: {
            "accuracy": r.accuracy,
            "attempts": r.attempts_count,
            "correct": r.correct_count,
            "last_word": r.last_word,
            "last_practiced_at": r.last_practiced_at.isoformat() if r.last_practiced_at else None,
        }
        for r in rows
    }


async def get_weak_phonemes(
    db: AsyncSession,
    patient_id: uuid.UUID,
    min_attempts: int = 2,
    limit: int = 5,
) -> List[str]:
    """Phonemes this child has practiced at least `min_attempts` times,
    sorted worst-accuracy-first. Other games / agent logic should call
    this directly (import this module, pass their own db session) when
    deciding what to drill next -- mirrors phoneme_drill.py's
    detect_struggling_phonemes(), but reads the persisted aggregate
    instead of an in-memory attempt_history list, so it works across
    sessions and across whichever specific game the child is in."""
    rows = (await db.execute(
        select(PhonemeMastery)
        .where(PhonemeMastery.patient_id == patient_id, PhonemeMastery.attempts_count >= min_attempts)
        .order_by(PhonemeMastery.accuracy.asc())
        .limit(limit)
    )).scalars().all()
    return [r.phoneme for r in rows]
