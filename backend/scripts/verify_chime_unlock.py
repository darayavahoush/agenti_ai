"""
One-off: write a synthetic RocketLaunch 'level_complete' event for a
throwaway test account (CHICK69 -- already-deactivated koyya duplicate,
safe to touch), then run the exact same getPassedLevels/getUnlockedLevels
logic levelProgress.js uses, in Python, against the real event row that
comes back from data_store.get_events() -- to see directly whether level
'oo' (SubmarineDive) actually unlocks or not, instead of guessing from
reading the JS.

Run from backend/, pointed at the real Azure DB:
    DATABASE_URL="postgresql+asyncpg://vaaksudhiadmin:Vaaksudhi123@vaaksudhi-db.postgres.database.azure.com:5432/vaaksudhi?ssl=require" \
    python -m scripts.verify_chime_unlock
"""
import asyncio
import uuid

from app.retraining import data_store

LEVEL_ORDER = ['aa', 'oo', 'ma', 'fa', 'ha', 'ee', 'r', 'village-builder']
PASS_THRESHOLD = 0.6

# CHICK69 -- an already-deactivated koyya duplicate test account.
CHILD_ID = uuid.UUID('d962a85e-ce79-426a-90db-a888870c99bb')


def get_passed_levels(events):
    """Python port of levelProgress.js's getPassedLevels(), applied to
    real event dicts instead of guessed-at JSON shapes."""
    passed = {}
    for level_id in LEVEL_ORDER:
        passed[level_id] = any(
            e['level_id'] == level_id
            and e['is_valid_attempt']
            and (e['score'] >= PASS_THRESHOLD or e['action'] == 'level_complete')
            for e in events
        )
    return passed


def get_unlocked_levels(passed):
    """Python port of levelProgress.js's getUnlockedLevels()."""
    unlocked = {}
    for i, level_id in enumerate(LEVEL_ORDER):
        unlocked[level_id] = i == 0 or bool(passed.get(LEVEL_ORDER[i - 1]))
    return unlocked


def main():
    print(f"Writing synthetic 'aa' level_complete event for {CHILD_ID}...")
    data_store.add_event(
        child_id=CHILD_ID, level_id='aa', attempt_number=1, score=1.0,
        is_valid_attempt=True, action='level_complete',
    )

    events = data_store.get_events(child_id=CHILD_ID)
    print(f"\n{len(events)} raw event(s) for this child:")
    for e in events:
        print({k: e[k] for k in ('level_id', 'score', 'is_valid_attempt', 'action')})

    passed = get_passed_levels(events)
    unlocked = get_unlocked_levels(passed)

    print("\npassed:  ", passed)
    print("unlocked:", unlocked)

    if unlocked.get('oo'):
        print("\n✅ 'oo' (SubmarineDive, level 2) unlocks correctly given this data.")
    else:
        print("\n❌ 'oo' (SubmarineDive, level 2) did NOT unlock -- real bug confirmed, keep digging here.")


if __name__ == "__main__":
    main()
