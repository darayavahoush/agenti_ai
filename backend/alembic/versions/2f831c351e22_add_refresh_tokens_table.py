"""add refresh tokens table

Revision ID: 2f831c351e22
Revises: a9f3c7d2e1b4
Create Date: 2026-08-20 09:29:20.786784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2f831c351e22'
down_revision: Union[str, Sequence[str], None] = 'a9f3c7d2e1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Already included in 000baseline0_baseline_schema.py."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_breathquest_refresh_tokens_token_hash'), table_name='breathquest_refresh_tokens')
    op.drop_index(op.f('ix_breathquest_refresh_tokens_owner_id'), table_name='breathquest_refresh_tokens')
    op.drop_table('breathquest_refresh_tokens')
