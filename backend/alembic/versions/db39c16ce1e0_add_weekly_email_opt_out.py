"""add weekly_email_opt_out to breathquest_patients

Revision ID: h8i9j0k1l2m3
Revises: acbe12154469
Create Date: 2026-09-17 00:00:00.000000

The weekly progress/nudge emails (see app/breathquest_core/
weekly_update.py's maybe_send_weekly_update) had no opt-out at all --
every parent with an email on file got emailed every week indefinitely.
Non-nullable with a server default of false so every existing patient
stays opted in (unchanged current behavior) until they explicitly turn
it off, either via the unsubscribe link in the email footer or the
toggle in Parent Settings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'db39c16ce1e0'
down_revision: Union[str, Sequence[str], None] = '886d2530f785'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'breathquest_patients',
        sa.Column('weekly_email_opt_out', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    op.drop_column('breathquest_patients', 'weekly_email_opt_out')
