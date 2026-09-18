"""
services/phoneme_summary.py — merges per-phoneme accuracy across
Flashcards (PhonemeMastery), VaakMirror (Attempt), and Chime
(RLTrainingEvent, via app.retraining.data_store) into one cross-game
view for the therapist dashboard.

Reads three independently-owned data sources, each with its own
accuracy convention:
  - PhonemeMastery.accuracy is 0-100 (see flashcards_models.py's own
    comment: "correct_count/attempts_count*100, denormalised for cheap
    ORDER BY"). Normalised to 0-1 here to match the other two.
  - VaakMirror Attempt has no stored accuracy — outcome is one of
    passed/caught/missed (AttemptOutcome); passed/caught count as
    correct, mirroring get_sound_progress()'s existing convention in
    routers/breathquest/dashboard.py.
  - Chime's RLTrainingEvent has is_valid_attempt (bool), same
    convention get_sound_progress() already uses for Chime.

Only phonemes phoneme_crosswalk.py can actually map are counted here —
sounds with no canonical mapping (VaakMirror blends/combos, Chime's
"ma"/"word" levels, etc.) are silently excluded rather than guessed at.
This is a read-only aggregation: nothing here writes to any table.
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flashcards_models import PhonemeMastery
from app.models.vaakmirror_models import Attempt, VaakMirrorSession, AttemptOutcome
from app.retraining import data_store as chime_data_store
from app.routers.flashcards.phoneme_data import PHONEME_DATA
from app.services.phoneme_crosswalk import (
    SUPPLEMENTAL_PHONEMES,
    vaakmirror_sound_to_phoneme,
    chime_level_to_phoneme,
)

# Phonemes attempted fewer than this many times, combined across all
# games, are excluded from the "weakest" priority list — a single lucky
# or unlucky attempt shouldn't rank a phoneme as a top priority.
MIN_ATTEMPTS_FOR_WEAKEST = 3
MAX_WEAKEST = 8


def _phoneme_meta(phoneme: str) -> dict:
    """PHONEME_DATA first, falling back to the two supplemental entries
    (AA, NG) that VaakMirror/Chime measure but Flashcards doesn't drill
    — see phoneme_crosswalk.py's module docstring for why those two
    live there instead of being patched into PHONEME_DATA itself."""
    return PHONEME_DATA.get(phoneme) or SUPPLEMENTAL_PHONEMES.get(phoneme) or {}


class _Acc:
    """Accumulator for one phoneme: totals plus a per-game breakdown."""

    __slots__ = ("attempts", "correct", "by_game", "last_practiced_at")

    def __init__(self):
        self.attempts = 0
        self.correct = 0
        self.by_game: dict[str, list[int, int]] = {}  # game -> [attempts, correct]
        self.last_practiced_at: Optional[datetime] = None

    def add(self, game: str, attempts: int, correct: int, when: Optional[datetime]):
        self.attempts += attempts
        self.correct += correct
        bucket = self.by_game.setdefault(game, [0, 0])
        bucket[0] += attempts
        bucket[1] += correct
        if when and (self.last_practiced_at is None or when > self.last_practiced_at):
            self.last_practiced_at = when


async def get_cross_game_phoneme_summary(
    db: AsyncSession,
    patient_id: str,
    chime_db_path=None,
) -> dict:
    """Returns a plain dict shaped like CrossGamePhonemeSummaryOut
    (schemas/breathquest_schemas.py) — the router wraps it in the
    Pydantic model. Queries the three sources, then hands the raw rows
    to _build_summary() (pure, no I/O) to do the actual merge — kept
    separate so the merge math can be unit-tested with fixture rows
    instead of a live DB."""
    fc_rows = (await db.execute(
        select(PhonemeMastery).where(PhonemeMastery.patient_id == patient_id)
    )).scalars().all()
    fc_tuples = [
        (r.phoneme, r.attempts_count, r.correct_count, r.last_practiced_at)
        for r in fc_rows if r.attempts_count
    ]

    vm_rows = (await db.execute(
        select(Attempt.sound_id, Attempt.outcome, Attempt.created_at)
        .join(VaakMirrorSession, Attempt.session_id == VaakMirrorSession.id)
        .where(
            VaakMirrorSession.patient_id == str(patient_id),
            Attempt.sound_id.isnot(None),
        )
    )).all()

    chime_events = await asyncio.to_thread(
        chime_data_store.get_events, child_id=str(patient_id), db_path=chime_db_path
    )

    return _build_summary(patient_id, fc_tuples, vm_rows, chime_events)


def _build_summary(patient_id, fc_tuples, vm_rows, chime_events) -> dict:
    """Pure merge: no DB/network access, only the fixture-friendly rows
    the three sources produce. fc_tuples: (phoneme, attempts, correct,
    last_practiced_at). vm_rows: (sound_id, outcome, created_at) —
    outcome may be an AttemptOutcome enum member or its .value string,
    both handled. chime_events: list of dicts with level_id,
    is_valid_attempt, timestamp, as returned by data_store.get_events()."""
    acc: dict[str, _Acc] = {}

    # ---- Flashcards: already-aggregated per-phoneme rows -------------
    for phoneme, attempts, correct, last_practiced_at in fc_tuples:
        acc.setdefault(phoneme, _Acc()).add("flashcards", attempts, correct, last_practiced_at)

    # ---- VaakMirror: raw attempts, mapped sound_id -> phoneme --------
    for sound_id, outcome, created_at in vm_rows:
        phoneme = vaakmirror_sound_to_phoneme(sound_id)
        if not phoneme:
            continue
        outcome_str = outcome.value if hasattr(outcome, "value") else str(outcome)
        is_correct = outcome_str in (AttemptOutcome.passed.value, AttemptOutcome.caught.value)
        acc.setdefault(phoneme, _Acc()).add("vaakmirror", 1, 1 if is_correct else 0, created_at)

    # ---- Chime: raw events, mapped level_id -> phoneme ---------------
    for ev in chime_events:
        phoneme = chime_level_to_phoneme(ev.get("level_id"))
        if not phoneme:
            continue
        ts = ev.get("timestamp")
        if not isinstance(ts, datetime):
            ts = None
        acc.setdefault(phoneme, _Acc()).add("chime", 1, 1 if ev.get("is_valid_attempt") else 0, ts)

    # ---- Assemble per-phoneme output ----------------------------------
    phonemes_out = []
    for phoneme, a in acc.items():
        meta = _phoneme_meta(phoneme)
        by_game = [
            {
                "game": game,
                "attempts": counts[0],
                "correct": counts[1],
                "accuracy": (counts[1] / counts[0]) if counts[0] else 0.0,
            }
            for game, counts in sorted(a.by_game.items())
        ]
        phonemes_out.append({
            "phoneme": phoneme,
            "ipa": meta.get("ipa"),
            "example_word": meta.get("example_word"),
            "category": meta.get("category"),
            "attempts": a.attempts,
            "correct": a.correct,
            "accuracy": (a.correct / a.attempts) if a.attempts else 0.0,
            "by_game": by_game,
            "last_practiced_at": a.last_practiced_at,
        })
    phonemes_out.sort(key=lambda p: p["accuracy"])

    # ---- Roll up by articulatory category ------------------------------
    cat_acc: dict[str, list[int, int]] = {}
    for p in phonemes_out:
        cat = p["category"] or "other"
        bucket = cat_acc.setdefault(cat, [0, 0])
        bucket[0] += p["attempts"]
        bucket[1] += p["correct"]
    by_category = [
        {
            "category": cat,
            "attempts": counts[0],
            "correct": counts[1],
            "accuracy": (counts[1] / counts[0]) if counts[0] else 0.0,
        }
        for cat, counts in sorted(cat_acc.items(), key=lambda kv: kv[1][0], reverse=True)
    ]

    weakest = [
        p for p in phonemes_out if p["attempts"] >= MIN_ATTEMPTS_FOR_WEAKEST
    ][:MAX_WEAKEST]

    total_attempts = sum(p["attempts"] for p in phonemes_out)
    total_correct = sum(p["correct"] for p in phonemes_out)

    return {
        "patient_id": str(patient_id),
        "phonemes": phonemes_out,
        "by_category": by_category,
        "weakest": weakest,
        "total_attempts": total_attempts,
        "overall_accuracy": (total_correct / total_attempts) if total_attempts else 0.0,
    }
