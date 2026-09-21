"""add editable @username to kid, parent and therapist accounts

Revision ID: d3a5d17961ee
Revises: f3a1b5c8d9e2
Create Date: 2026-09-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd3a5d17961ee'
down_revision: Union[str, Sequence[str], None] = 'f3a1b5c8d9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, index name). Nullable + unique index on each: existing accounts have
# no username until they pick one via the first-login prompt, and Postgres
# allows any number of NULLs under a UNIQUE index. Cross-table uniqueness
# (a kid and a therapist can't share a handle) is enforced in the app layer --
# see app/breathquest_core/username.py.
_TABLES = [
    ('breathquest_patients', 'ix_breathquest_patients_username'),
    ('breathquest_parents', 'ix_breathquest_parents_username'),
    ('therapists', 'ix_therapists_username'),
]


def upgrade() -> None:
    for table, index in _TABLES:
        op.add_column(table, sa.Column('username', sa.String(length=30), nullable=True))
        op.create_index(index, table, ['username'], unique=True)


def downgrade() -> None:
    for table, index in reversed(_TABLES):
        op.drop_index(index, table_name=table)
        op.drop_column(table, 'username')
