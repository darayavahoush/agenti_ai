"""add unverified phone columns to therapists and parents

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-14

Backs the plain (unverified) phone field added to therapist/parent signup
alongside cutting the /verify email-OTP hop -- see Landing.jsx's comment on
that page for why that hop was removed. Both columns are simple contact
info collected on their own signup forms, unrelated to the kid-signup
COPPA consent flow (breathquest_phone_verifications /
breathquest_patients.parent_phone from d4e5f6a7b8c9), which is unaffected
and stays exactly as-is:
  - therapists.phone
  - breathquest_parents.phone

Both nullable since existing accounts predate this field, and neither is
verified -- there's no SMS provider wired up for either role yet (only the
kid-consent path in d4e5f6a7b8c9 has real OTP verification).

Chains on d4e5f6a7b8c9, the real current head on main as of this
migration.

Hand-written, same reasoning as the prior four migrations: no live DB in
this sandbox to autogenerate against.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Already included in 000baseline0_baseline_schema.py.
    pass

def downgrade() -> None:
    op.drop_column("breathquest_parents", "phone")
    op.drop_column("therapists", "phone")
