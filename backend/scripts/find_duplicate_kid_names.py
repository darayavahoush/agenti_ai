"""
One-off diagnostic: list BreathQuestPatient rows that share a first_name
(case-insensitive), so you can see exactly which player_code is which kid
before deactivating/merging any duplicates.

first_name has never had a uniqueness constraint -- kid_register() and
parent_kid_register() in routers/breathquest/auth.py don't check for an
existing patient with the same name before creating a new one. player_code
is the only real unique identifier; this script surfaces the collisions
that causes for name-based kid login.

Run from backend/:
    python -m scripts.find_duplicate_kid_names

Prints nothing sensitive -- no PINs (only hashes exist anyway, never
logged) and parent_email is partially masked.
"""
import asyncio
from collections import defaultdict

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.breathquest_models import BreathQuestPatient


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "(none)"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BreathQuestPatient).order_by(BreathQuestPatient.first_name, BreathQuestPatient.created_at)
        )
        patients = result.scalars().all()

    groups = defaultdict(list)
    for p in patients:
        groups[p.first_name.strip().lower()].append(p)

    dupes = {name: rows for name, rows in groups.items() if len(rows) > 1}

    if not dupes:
        print("No duplicate first_names found.")
        return

    print(f"{len(dupes)} name(s) with duplicate accounts, {sum(len(r) for r in dupes.values())} rows total:\n")
    for name, rows in dupes.items():
        print(f"=== {name!r} ({len(rows)} accounts) ===")
        for p in rows:
            print(
                f"  player_code={p.player_code:<10} "
                f"id={p.id}  "
                f"avatar={p.avatar or '-':<10} "
                f"therapist_id={p.therapist_id or '(self-registered)'}  "
                f"parent_email={_mask_email(p.parent_email)}  "
                f"active={p.is_active}  "
                f"created={p.created_at}"
            )
        print()


if __name__ == "__main__":
    asyncio.run(main())
