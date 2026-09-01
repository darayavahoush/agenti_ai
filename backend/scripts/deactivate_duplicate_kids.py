"""
One-off: soft-deactivate the extra rows in a duplicate first_name group,
keeping exactly one "real" account per name.

Never deletes anything -- only flips is_active to False, same flag the
app already checks elsewhere (login, dashboards). Reversible by hand
(UPDATE breathquest_patients SET is_active=true WHERE player_code=...)
if you pick the wrong one to keep.

Which row is "kept" per name group:
  1. If any row in the group has at least one GameSession, keep the one
     whose most recent session (GameSession.started_at) is latest --
     i.e. whoever actually played most recently is treated as the real,
     in-use account.
  2. If NO row in the group has any sessions at all (e.g. a burst of
     never-played self-registration duplicates), keep the earliest
     created_at instead, on the assumption the first registration is
     the real one and the rest were accidental re-registrations.

Everything else in the group gets is_active=False.

Defaults to a DRY RUN -- prints exactly what it would change and does
not touch the DB. Pass --confirm to actually apply.

Run from backend/:
    python -m scripts.deactivate_duplicate_kids                # dry run, all dupe groups
    python -m scripts.deactivate_duplicate_kids --name koyya    # dry run, just one group
    python -m scripts.deactivate_duplicate_kids --name koyya --confirm   # apply it

Prints nothing sensitive -- no PINs, parent_email is partially masked.
"""
import argparse
import asyncio
from collections import defaultdict

from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.breathquest_models import BreathQuestPatient, GameSession
import app.models.patient  # noqa: F401 -- registers `patients` table so the
                            # assessment_patient_id FK on BreathQuestPatient
                            # resolves at commit time; unused directly here.
import app.models.therapist  # noqa: F401 -- registers `therapists` table so the
                              # therapist_id FK on BreathQuestPatient resolves
                              # too; unused directly here.


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "(none)"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


async def main(name_filter: str | None, confirm: bool):
    async with AsyncSessionLocal() as db:
        patients = (
            await db.execute(
                select(BreathQuestPatient)
                .where(BreathQuestPatient.is_active == True)  # noqa: E712 -- already-inactive rows aren't candidates
                .order_by(BreathQuestPatient.first_name, BreathQuestPatient.created_at)
            )
        ).scalars().all()

        # last activity per patient_id, in one query rather than N+1
        last_activity_rows = (
            await db.execute(
                select(GameSession.patient_id, func.max(GameSession.started_at))
                .group_by(GameSession.patient_id)
            )
        ).all()
        last_activity = {pid: ts for pid, ts in last_activity_rows}

    groups = defaultdict(list)
    for p in patients:
        groups[p.first_name.strip().lower()].append(p)

    dupes = {name: rows for name, rows in groups.items() if len(rows) > 1}
    if name_filter:
        dupes = {name: rows for name, rows in dupes.items() if name == name_filter.strip().lower()}

    if not dupes:
        print("No matching duplicate-name groups found among active accounts.")
        return

    to_deactivate: list[BreathQuestPatient] = []

    for name, rows in dupes.items():
        any_activity = any(last_activity.get(p.id) is not None for p in rows)
        if any_activity:
            keep = max(rows, key=lambda p: (last_activity.get(p.id) is not None, last_activity.get(p.id) or p.created_at))
            reason = "most recent activity"
        else:
            keep = min(rows, key=lambda p: p.created_at)
            reason = "no rows have any sessions -- keeping earliest-created"

        print(f"=== {name!r} ({len(rows)} active accounts) -- keeping by: {reason} ===")
        for p in rows:
            marker = "KEEP" if p.id == keep.id else "deactivate"
            last_seen = last_activity.get(p.id)
            print(
                f"  [{marker:<10}] player_code={p.player_code:<10} "
                f"id={p.id}  "
                f"parent_email={_mask_email(p.parent_email)}  "
                f"created={p.created_at}  "
                f"last_session={last_seen or '(never played)'}"
            )
            if p.id != keep.id:
                to_deactivate.append(p)
        print()

    if not confirm:
        print(f"DRY RUN -- would deactivate {len(to_deactivate)} row(s) above. Re-run with --confirm to apply.")
        return

    async with AsyncSessionLocal() as db:
        ids = [p.id for p in to_deactivate]
        rows = (
            await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id.in_(ids)))
        ).scalars().all()
        for p in rows:
            p.is_active = False
        await db.commit()

    print(f"Deactivated {len(to_deactivate)} row(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="Only process this one duplicate-name group (case-insensitive)")
    parser.add_argument("--confirm", action="store_true", help="Actually apply the deactivation (default: dry run)")
    args = parser.parse_args()
    asyncio.run(main(args.name, args.confirm))
