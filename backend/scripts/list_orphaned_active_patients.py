"""
Read-only companion to scripts.backfill_assessment_links: prints
identifying info for active BreathQuestPatient rows with no
therapist_id, to help a human pick the right therapist for
POST /patients/link. Never writes anything.

Run from backend/:
    python3 -m scripts.list_orphaned_active_patients
"""
import asyncio

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
        orphans = (
            await db.execute(
                select(BreathQuestPatient)
                .where(
                    BreathQuestPatient.therapist_id.is_(None),
                    BreathQuestPatient.is_active.is_(True),
                )
                .order_by(BreathQuestPatient.created_at)
            )
        ).scalars().all()

    if not orphans:
        print("No active, therapist-less BreathQuestPatient rows found.")
        return

    print(f"{len(orphans)} active row(s) with no therapist:\n")
    for p in orphans:
        print(
            f"  player_code={p.player_code:<10} first_name={p.first_name:<15} "
            f"username={p.username or '(none)':<15} parent_email={_mask_email(p.parent_email):<20} "
            f"created={p.created_at}"
        )


if __name__ == "__main__":
    asyncio.run(main())
