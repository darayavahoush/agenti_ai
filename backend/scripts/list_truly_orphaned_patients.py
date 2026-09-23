"""
Corrected version of list_orphaned_active_patients: that script (and
backfill_assessment_links) only checked BreathQuestPatient.therapist_id
and .parent_email, but a child added via the multi-child "add another
child" flow (auth.py's add_child(), 2026-09-10) deliberately has BOTH
null -- its owning Parent is tracked only through the
breathquest_parent_children join table. Treating "no therapist_id, no
parent_email" as "orphaned" therefore wrongly flags real, normally-owned
parent accounts.

This checks all three ownership paths (Parent via ParentChild,
BreathQuestPatient.parent_email, BreathQuestPatient.therapist_id) and
only reports a row as truly orphaned if none of them are present.

Run from backend/:
    python3 -m scripts.list_truly_orphaned_patients
"""
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.breathquest_models import BreathQuestPatient, ParentChild, Parent


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "(none)"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


async def main():
    async with AsyncSessionLocal() as db:
        active_no_therapist = (
            await db.execute(
                select(BreathQuestPatient)
                .where(
                    BreathQuestPatient.therapist_id.is_(None),
                    BreathQuestPatient.is_active.is_(True),
                )
                .order_by(BreathQuestPatient.created_at)
            )
        ).scalars().all()

        if not active_no_therapist:
            print("No active, therapist-less BreathQuestPatient rows found.")
            return

        ids = [p.id for p in active_no_therapist]
        parent_links = (
            await db.execute(
                select(ParentChild.patient_id, Parent.email)
                .join(Parent, Parent.id == ParentChild.parent_id)
                .where(ParentChild.patient_id.in_(ids))
            )
        ).all()
        parent_email_by_patient = {pid: email for pid, email in parent_links}

    owned_by_parent = []
    truly_orphaned = []
    for p in active_no_therapist:
        linked_parent_email = parent_email_by_patient.get(p.id) or p.parent_email
        if linked_parent_email:
            owned_by_parent.append((p, linked_parent_email))
        else:
            truly_orphaned.append(p)

    print(f"=== {len(owned_by_parent)} row(s) with no therapist but a real parent (via ParentChild or parent_email) ===")
    print("These are working as designed -- no therapist assigned yet, not data debt:\n")
    for p, email in owned_by_parent:
        print(f"  player_code={p.player_code:<10} first_name={p.first_name:<15} parent={_mask_email(email)}")

    print()
    print(f"=== {len(truly_orphaned)} row(s) with NO owner anywhere (no therapist, no parent, no parent_email) ===")
    print("These are the ones that actually need manual triage:\n")
    for p in truly_orphaned:
        print(
            f"  player_code={p.player_code:<10} first_name={p.first_name:<15} "
            f"username={p.username or '(none)':<15} created={p.created_at}"
        )


if __name__ == "__main__":
    asyncio.run(main())
