"""add last_weekly_email_sent_at to breathquest_patients

Revision ID: g7h8i9j0k1l2
Revises: b4c5d6e7f8a9
Create Date: 2026-08-30 11:46:00.000000

Supports the weekly parent progress-update email (see
app/breathquest_core/weekly_update.py's maybe_send_weekly_update), which
follows the same lazy-checkpoint shape as app/retraining/scheduler.py's
run_retrain_if_due: rather than a real cron/Celery schedule (this project
has none -- a single uvicorn process, no background worker), the check
runs opportunistically on kid_login and compares "now" against this
timestamp to decide whether a week has elapsed. Nullable: on a patient's
very first login-triggered check with no prior send, the window falls
back to "7 days ago" rather than being blocked forever on a missing value
-- same nullable reasoning as assessment_completed_at above it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k1l2'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'breathquest_patients',
        sa.Column('last_weekly_email_sent_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('breathquest_patients', 'last_weekly_email_sent_at')
