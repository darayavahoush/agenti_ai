"""
One-off: deactivate a specific list of BreathQuestPatient rows by
player_code. For the 5 rows identified via scripts.list_truly_orphaned_patients
as having no owner anywhere in the schema (no therapist, no parent via
ParentChild, no parent_email) -- either pre-dates both the COPPA
parent-email requirement and multi-child support (CHICK40, CHICK53,
PC724DBBAD, PC01ED4074), or is a leftover test account (TESTLOGIN).

Only ever sets is_active=False -- same flag the app already checks
everywhere (login, dashboards), same as deactivate_duplicate_kids.py.
Never deletes anything, reversible by hand
(UPDATE breathquest_patients SET is_active=true WHERE player_code=...)
if a code was included by mistake.

Defaults to a DRY RUN -- prints what it would change and does not
touch the DB. Pass --confirm to actually apply.

Run from backend/:
    python3 -m scripts.deactivate_by_player_code --codes CHICK40,CHICK53,PC724DBBAD,PC01ED4074,TESTLOGIN
    python3 -m scripts.deactivate_by_player_code --codes CHICK40,CHICK53,PC724DBBAD,PC01ED4074,TESTLOGIN --confirm
"""
import argparse
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.breathquest_models import BreathQuestPatient


async def main(codes: list[str], confirm: bool):
    codes = [c.strip().upper() for c in codes if c.strip()]
    if not codes:
        print("No player codes given.")
        return

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(BreathQuestPatient).where(BreathQuestPatient.player_code.in_(codes))
            )
        ).scalars().all()

    found_codes = {p.player_code for p in rows}
    missing = [c for c in codes if c not in found_codes]
    if missing:
        print(f"WARNING: no row found for: {', '.join(missing)} -- check spelling/case, these will be skipped.\n")

    already_inactive = [p for p in rows if not p.is_active]
    to_deactivate = [p for p in rows if p.is_active]

    if already_inactive:
        print(f"Already inactive, no change needed: {', '.join(p.player_code for p in already_inactive)}\n")

    if not to_deactivate:
        print("Nothing left to deactivate.")
        return

    print(f"Would deactivate {len(to_deactivate)} row(s):")
    for p in to_deactivate:
        print(f"  player_code={p.player_code:<10} first_name={p.first_name:<15} created={p.created_at}")

    if not confirm:
        print("\nDRY RUN -- re-run with --confirm to apply.")
        return

    async with AsyncSessionLocal() as db:
        ids = [p.id for p in to_deactivate]
        rows = (
            await db.execute(select(BreathQuestPatient).where(BreathQuestPatient.id.in_(ids)))
        ).scalars().all()
        for p in rows:
            p.is_active = False
        await db.commit()

    print(f"\nDeactivated {len(to_deactivate)} row(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes", required=True, help="Comma-separated player codes, e.g. CHICK40,TESTLOGIN")
    parser.add_argument("--confirm", action="store_true", help="Actually apply the deactivation (default: dry run)")
    args = parser.parse_args()
    asyncio.run(main(args.codes.split(","), args.confirm))
