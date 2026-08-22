"""add google_sub columns and nullable hashed_password for Google Sign-In

Revision ID: a3b4c5d6e7f8
Revises: 71ec5364b35a
Create Date: 2026-08-22 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = '71ec5364b35a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('therapists', sa.Column('google_sub', sa.String(), nullable=True))
    op.create_index(op.f('ix_therapists_google_sub'), 'therapists', ['google_sub'], unique=True)
    op.alter_column('therapists', 'hashed_password', existing_type=sa.String(), nullable=True)

    op.add_column('breathquest_parents', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_breathquest_parents_google_sub'), 'breathquest_parents', ['google_sub'], unique=True)
    op.alter_column('breathquest_parents', 'hashed_password', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # Reverting hashed_password to NOT NULL would fail if any Google-only
    # (password-less) accounts were created while this migration was
    # applied -- same class of problem as any other nullable-relaxation
    # migration's downgrade, left as a manual step if that ever comes up
    # rather than silently deleting/backfilling data here.
    op.drop_index(op.f('ix_breathquest_parents_google_sub'), table_name='breathquest_parents')
    op.drop_column('breathquest_parents', 'google_sub')

    op.drop_index(op.f('ix_therapists_google_sub'), table_name='therapists')
    op.drop_column('therapists', 'google_sub')
