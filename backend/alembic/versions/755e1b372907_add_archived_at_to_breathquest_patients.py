"""add archived_at to breathquest_patients

Revision ID: 755e1b372907
Revises: db39c16ce1e0
Create Date: 2026-09-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '755e1b372907'
down_revision: Union[str, Sequence[str], None] = 'db39c16ce1e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, zero-risk to existing rows. Paired with the already-existing
    # is_active column: archive sets is_active=False, archived_at=utcnow();
    # restore sets is_active=True, archived_at=None. is_active already gates
    # login (see breathquest_core/deps.py's get_current_patient), so archive
    # reuses that dormant field rather than adding a second status column.
    op.add_column(
        'breathquest_patients',
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('breathquest_patients', 'archived_at')
