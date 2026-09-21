"""add last_seen_at to breathquest_patients

Revision ID: f3a1b5c8d9e2
Revises: 755e1b372907
Create Date: 2026-09-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f3a1b5c8d9e2'
down_revision: Union[str, Sequence[str], None] = '755e1b372907'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, zero-risk to existing rows. Bumped on every authenticated
    # kid request (see breathquest_core/deps.py's get_current_patient) so
    # the therapist dashboard can show a real "Logged in" status (#69)
    # instead of the account-enabled is_active flag it was showing before.
    op.add_column(
        'breathquest_patients',
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('breathquest_patients', 'last_seen_at')
