"""add assessment_patient_id to breathquest_patients

Revision ID: a9f3c7d2e1b4
Revises: ceee54dbbe44
Create Date: 2026-08-15 20:05:00.000000

Fixed 2026-08-20: originally authored with revision="a1b2c3d4e5f6" and
down_revision=None -- an accidental collision with the actual first
migration in this project (add_breathquest_patient_assessment_columns.py,
also "a1b2c3d4e5f6"/None), created independently around the same time.
Both wrongly claimed to be root, leaving two disconnected heads -- a
fresh DB running `alembic upgrade head` would only apply whichever one
Alembic happened to pick, silently skipping the other's columns.

Re-chained here onto the real current head (ceee54dbbe44) instead of
its true chronological position, since we don't know what order any
already-deployed database actually applied these changes in and
rewriting history in the middle of the chain risks breaking one that
did it differently. The columns/FK/index this migration adds already
exist in every environment that's been running -- see this repo's
notes on stamping rather than re-running upgrade() where that's true.

Constraint name also corrected below (breathquest_patients_assessment_patient_id_fkey,
not fk_breathquest_patients_assessment_patient_id_patients) to match
what's actually deployed -- the original name would make `alembic
downgrade` fail trying to drop a constraint that doesn't exist under
that name.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a9f3c7d2e1b4'
down_revision = 'ceee54dbbe44'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'breathquest_patients',
        sa.Column('assessment_patient_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f('ix_breathquest_patients_assessment_patient_id'),
        'breathquest_patients', ['assessment_patient_id'], unique=True,
    )
    op.create_foreign_key(
        'breathquest_patients_assessment_patient_id_fkey',
        'breathquest_patients', 'patients',
        ['assessment_patient_id'], ['id'],
    )


def upgrade() -> None:
    """Already included in 000baseline0_baseline_schema.py."""
    pass