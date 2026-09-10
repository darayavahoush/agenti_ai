"""add feedback columns to rl_training_events

Revision ID: 6c5d9da5ce73
Revises: h8i9j0k1l2m3
Create Date: 2026-09-10 11:29:07.962804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c5d9da5ce73'
down_revision: Union[str, Sequence[str], None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('breathquest_rl_training_events', sa.Column('feedback', sa.String(), nullable=True))
    op.add_column('breathquest_rl_training_events', sa.Column('feedback_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('breathquest_rl_training_events', 'feedback_at')
    op.drop_column('breathquest_rl_training_events', 'feedback')
