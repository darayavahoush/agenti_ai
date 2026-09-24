"""
One-off: backfill assessment_patient_id for legacy BreathQuestPatient rows
that predate the FK (added 2026-08-15, migration a9f3c7d2e1b4) or the
create_patient() link-on-creation fix (2026-08-13).

Without this link, a real, actively-playing patient 404s on every
agent-status / diagnostic route (see docs/DATA_MODEL.md) even though
nothing is actually wrong with their account -- the only existing path
that fixes this is /patients/{id}/start-session, which only runs once a
therapist happens to launch a session for that specific kid. This script
does the same thing proactively, in bulk, for every affected row.

Two groups, handled differently:

1. therapist_id IS SET, assessment_patient_id IS NULL
   -> Safe to backfill. Creates the linked Assessment-side Patient row
      and sets assessment_patient_id, exactly like start_session()'s
      lazy backfill does for one patient at a time.

2. therapist_id IS NULL (assessment_patient_id also always NULL here,
   since nothing has ever been able to reach these rows to set either)
   -> NOT auto-fixed. There's no reliable signal anywhere in the schema
      (GameSession has no therapist reference either) for which
      therapist should own one of these -- guessing would silently
      hand a therapist someone else's patient. Reported only, for a
      human to resolve via /patients/link (or a DB update once the
      right therapist is confirmed some other way, e.g. support ticket).

Defaults to a DRY RUN -- prints exactly what it would create and does
not touch the DB. Pass --confirm to actually apply.

Run from backend/:
    python -m scripts.backfill_assessment_links             # dry run
    python -m scripts.backfill_assessment_links --confirm   # apply
"""
import argparse
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.breathquest_models import BreathQuestPatient
from app.models.patient import Patient
import app.models.therapist  # noqa: F401 -- registers `therapists` table so the
                              # therapist_id FK on BreathQuestPatient resolves.


async def main(confirm: bool):
    async with AsyncSessionLocal() as db:
        unlinked = (
            await db.execute(
                select(BreathQuestPatient)
                .where(BreathQuestPatient.assessment_patient_id.is_(None))
                .order_by(BreathQuestPatient.created_at)
            )
        ).scalars().all()

    if not unlinked:
        print("No BreathQuestPatient rows are missing assessment_patient_id. Nothing to do.")
        return

    fixable = [p for p in unlinked if p.therapist_id is not None]
    orphaned = [p for p in unlinked if p.therapist_id is None]

    print(f"=== {len(fixable)} row(s) with a therapist -- will backfill the assessment link ===")
    for p in fixable:
        print(f"  player_code={p.player_code:<10} id={p.id}  therapist_id={p.therapist_id}  created={p.created_at}")

    print()
    print(f"=== {len(orphaned)} row(s) with NO therapist -- cannot auto-link, needs manual review ===")
    for p in orphaned:
        print(f"  player_code={p.player_code:<10} id={p.id}  created={p.created_at}  "
              f"is_active={p.is_active}  -- resolve via POST /patients/link once the right therapist is known")

    if not confirm:
        print()
        print(f"DRY RUN -- would create {len(fixable)} Patient row(s) and link them above. "
              f"Re-run with --confirm to apply. The {len(orphaned)} orphaned row(s) are never "
              f"auto-fixed by this script regardless.")
        return

    async with AsyncSessionLocal() as db:
        ids = [p.id for p in fixable]
        rows = (
            await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id.in_(ids)))
        ).scalars().all()
        for p in rows:
            assessment_patient = Patient(
                name=p.first_name,
                age=p.age,
                diagnosis=p.diagnosis_notes,
                registered_therapist_id=p.therapist_id,
            )
            db.add(assessment_patient)
            await db.flush()  # populate assessment_patient.id before referencing it
            p.assessment_patient_id = assessment_patient.id
        await db.commit()

    print(f"Linked {len(fixable)} row(s). {len(orphaned)} orphaned row(s) still need manual review (see above).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Actually apply the backfill (default: dry run)")
    args = parser.parse_args()
    asyncio.run(main(args.confirm))
