"""add assessment_completed_at for retake cooldown

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-08-24 09:00:00.000000

Supports the retake-with-cooldown flow (routers/breathquest/assessment.py):
assessment_completed alone can't tell us *when* a kid last finished, which
is needed to compute "eligible to retake in N days". Nullable since every
existing completed row predates this column -- see
assessment.py's _retake_available_at for how that's treated (eligible
immediately, not blocked forever on missing data).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'breathquest_patients',
        sa.Column('assessment_completed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('breathquest_patients', 'assessment_completed_at')
