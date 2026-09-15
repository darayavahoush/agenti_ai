"""fix stale therapist_id FK on breathquest_therapist_notes

Revision ID: acbe12154469
Revises: n4o5p6q7r8s9
Create Date: 2026-09-15 16:33:40.149468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acbe12154469'
down_revision: Union[str, Sequence[str], None] = 'n4o5p6q7r8s9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        'breathquest_therapist_notes_therapist_id_fkey',
        'breathquest_therapist_notes',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'breathquest_therapist_notes_therapist_id_fkey',
        'breathquest_therapist_notes', 'therapists',
        ['therapist_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'breathquest_therapist_notes_therapist_id_fkey',
        'breathquest_therapist_notes',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'breathquest_therapist_notes_therapist_id_fkey',
        'breathquest_therapist_notes', 'breathquest_therapists',
        ['therapist_id'], ['id'],
    )
