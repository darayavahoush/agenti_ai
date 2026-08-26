"""add avatar_photo_url to breathquest_patients

Revision ID: f2f2f66929d3
Revises: e5f6a7b8c9d0
Create Date: 2026-08-15 14:04:24.071780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2f2f66929d3'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Already included in 000baseline0_baseline_schema.py."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("breathquest_patients", "avatar_photo_url")
