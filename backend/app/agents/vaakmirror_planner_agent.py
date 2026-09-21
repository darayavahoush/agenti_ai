import logging
from collections import Counter

from app.services.alphabet_sounds import (
    LETTERS, CORE_LETTERS, MIN_LETTERS_FOR_PLAN, LIP_GROUPS, TONGUE_GROUPS,
)

logger = logging.getLogger(__name__)

# VaakMirror's own bounds (agent/round_size_heuristic.py: MIN/MAX_ROUND_SIZE).
MIN_ROUND, MAX_ROUND = 4, 20
DEFAULT_ROUND = 10


class VaakMirrorPlannerAgent:
    """
    Turns the Alphabet check's per-letter results into the parameters
    VaakMirror's games start with, so the mouth games open on THIS child's
    tricky sounds instead of a random pick.

    Parameters it sets (all consumed by the games, see frontend
    vaakmirror/lib/focusedRound.js and the useAgentParams hook):
      focus_sounds      VaakMirror sound ids to over-sample, trickiest first
      round_size        rounds per game (shorter when the child is struggling)
      start_complexity  "single" or "blend" for Mirror, Mirror's curriculum
      primary_game      which VaakMirror game to open with
    plus `suggested_next` letters to probe next and a plain-language summary.

    Deterministic on purpose: a therapist can see exactly why a setting was
    chosen, and the same results always give the same plan.
    """

    def analyze(self, state: dict) -> dict:
        # Only trust the letter itself from the caller: sound id and group are
        # always looked up from the catalog, never taken from the payload.
        results = []
        for r in state.get("letter_results") or []:
            if not isinstance(r, dict):
                continue
            letter = str(r.get("letter") or "").upper()
            if letter not in LETTERS:
                continue
            results.append({**r, "letter": letter, "word": LETTERS[letter]["word"],
                            "sound_id": LETTERS[letter]["vm"], "group": LETTERS[letter]["group"]})
        scored = [r for r in results if r.get("correct") is not None]
        missed = [r for r in scored if r["correct"] is False]
        got = [r for r in scored if r["correct"] is True]
        n = len(scored)
        miss_rate = len(missed) / n if n else 0.0

        # Trickiest first: repeated misses of the same sound rank higher.
        counts = Counter(r["sound_id"] for r in missed)
        focus = [sid for sid, _ in counts.most_common()]
        # A swap points at its look-alike partner too (k said as t -> practise both).
        for r in missed:
            for nxt in LETTERS.get(r["letter"], {}).get("next", [])[:1]:
                sid = LETTERS[nxt]["vm"]
                if sid not in focus and n >= MIN_LETTERS_FOR_PLAN and miss_rate >= 0.5:
                    focus.append(sid)

        if n == 0:
            round_size = DEFAULT_ROUND
        elif miss_rate >= 0.5:
            round_size = 6           # shorter rounds while it is hard
        elif miss_rate == 0:
            round_size = 12          # nothing tricky: stretch a little
        else:
            round_size = 8
        round_size = max(MIN_ROUND, min(MAX_ROUND, round_size))

        start_complexity = "blend" if (n >= MIN_LETTERS_FOR_PLAN and not missed) else "single"

        lip_miss = sum(1 for r in missed if r.get("group") in LIP_GROUPS)
        tongue_miss = sum(1 for r in missed if r.get("group") in TONGUE_GROUPS)
        if lip_miss > tongue_miss:
            primary = "lip_sync_hero"
        elif tongue_miss >= 2 and tongue_miss > lip_miss:
            primary = "tongue_tamer"
        else:
            primary = "mirror_mirror"

        tried = {r["letter"] for r in results}
        suggested = []
        for r in missed:
            for nxt in LETTERS.get(r["letter"], {}).get("next", []):
                if nxt not in tried and nxt not in suggested:
                    suggested.append(nxt)
        for c in CORE_LETTERS:
            if len(suggested) >= 3:
                break
            if c not in tried and c not in suggested:
                suggested.append(c)
        suggested = suggested[:3]

        plan = {
            "letters_checked": n,
            "ready": n >= MIN_LETTERS_FOR_PLAN,
            "nailed": [r["letter"] for r in got],
            "tricky": [{"letter": r["letter"], "sound_id": r["sound_id"], "heard_as": r.get("heard_as"),
                        "word": r.get("word")} for r in missed],
            "suggested_next": suggested,
            "vaakmirror_params": {
                "primary_game": primary,
                "focus_sounds": focus,
                "round_size": round_size,
                "start_complexity": start_complexity,
            },
            "summary": self._summary(n, got, missed, primary, round_size),
        }
        return {"plan": plan}

    @staticmethod
    def _summary(n, got, missed, primary, round_size) -> str:
        game = {"lip_sync_hero": "Lip Sync Hero", "tongue_tamer": "Tongue Tamer",
                "mirror_mirror": "Mirror, Mirror"}[primary]
        if n == 0:
            return "Say a few letter sounds and the agent will set up your mouth games."
        if not missed:
            return (f"Every sound you tried was clear. Your mouth games will start with a longer "
                    f"round of {round_size}, beginning with {game}.")
        tricky = ", ".join(f"\"{r['letter'].lower()}\"" for r in missed[:4])
        return (f"Tricky sounds: {tricky}. Your mouth games will open on these, in rounds of "
                f"{round_size}, starting with {game}.")
