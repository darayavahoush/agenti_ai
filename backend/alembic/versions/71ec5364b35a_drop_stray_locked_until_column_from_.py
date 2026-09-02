"""drop stray locked_until column from refresh tokens

Revision ID: 71ec5364b35a
Revises: 2f831c351e22
Create Date: 2026-08-20 09:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '71ec5364b35a'
down_revision: Union[str, Sequence[str], None] = '2f831c351e22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Already reflected in the existing database schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'breathquest_refresh_tokens',
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    )
