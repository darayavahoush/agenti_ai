"""
One-off diagnostic: list Parent and Therapist rows that share an email
address once case is ignored (e.g. "Jane@Gmail.com" and "jane@gmail.com"),
so you can see exactly which accounts collide before relying on
case-insensitive email lookups to always mean "the same account".

Parent.email and Therapist.email have always been plain, case-sensitive
`unique` columns, and (until the fix this script ships alongside) nothing
in the app normalized case before writing or comparing them -- so two
people (or one person, twice) could end up with what looks like the same
email but is actually two separate rows. Every register/login/reset path
now normalizes to lowercase and compares case-insensitively, which makes
existing case-variant duplicates behave unpredictably: whichever row a
case-insensitive query happens to return first "wins" a login, and the
other becomes permanently unreachable through the UI.

This script only reads and reports -- it changes nothing. If it finds any
group with more than one row, resolve them by hand (decide which account
is the real one, and deactivate/merge the other) before adding a DB-level
case-insensitive unique constraint, which would fail to apply while any
duplicates still exist.

Run from backend/:
    python -m scripts.find_case_duplicate_emails

Prints nothing sensitive -- no password hashes, and every email is
partially masked.
"""
import asyncio
from collections import defaultdict

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.breathquest_models import Parent
from app.models.therapist import Therapist


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "(none)"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


async def _report(label: str, rows, email_attr: str, extra_cols) -> int:
    groups = defaultdict(list)
    for row in rows:
        email = getattr(row, email_attr) or ""
        groups[email.strip().lower()].append(row)

    dupes = {key: group for key, group in groups.items() if len(group) > 1}

    if not dupes:
        print(f"{label}: no case-variant duplicate emails found.")
        return 0

    print(f"{label}: {len(dupes)} email(s) with duplicate accounts, "
          f"{sum(len(g) for g in dupes.values())} rows total:\n")
    for _key, group in dupes.items():
        print(f"=== {_mask_email(getattr(group[0], email_attr))} ({len(group)} accounts) ===")
        for row in group:
            cols = "  ".join(f"{name}={getattr(row, name)}" for name in extra_cols)
            print(f"  id={row.id}  email_as_stored={getattr(row, email_attr)!r}  {cols}")
        print()
    return len(dupes)


async def main():
    async with AsyncSessionLocal() as db:
        parents = (await db.execute(select(Parent).order_by(Parent.email, Parent.created_at))).scalars().all()
        therapists = (await db.execute(select(Therapist).order_by(Therapist.email))).scalars().all()

    parent_dupes = await _report(
        "Parent", parents, "email",
        extra_cols=["patient_id", "is_active", "created_at"],
    )
    print()
    therapist_dupes = await _report(
        "Therapist", therapists, "email",
        extra_cols=["is_active"],
    )

    if parent_dupes or therapist_dupes:
        print(
            "\nResolve the groups above (pick the real account, deactivate or "
            "merge the other) before adding any DB-level case-insensitive "
            "uniqueness -- it will fail to apply otherwise."
        )


if __name__ == "__main__":
    asyncio.run(main())
