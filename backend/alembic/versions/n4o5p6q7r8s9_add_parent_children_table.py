"""add breathquest_parent_children table for multi-child support

Revision ID: n4o5p6q7r8s9
Revises: 6c5d9da5ce73
Create Date: 2026-09-10 00:00:00.000000

Adds the many-to-many link a Parent account needs to switch between more
than one child (see AuthContext.jsx's switchChild / the new
POST /auth/parent/switch-child). Parent.patient_id itself is untouched --
it keeps meaning "the currently active child for this parent's session",
exactly as every existing parent.py/auth.py query already assumes -- this
table is purely the *set* of children a parent is allowed to switch it to.

Backfills one row per existing Parent (parent_id, parent.patient_id,
is_primary=True) so every account that already has a linked child keeps
working identically the moment this lands, with no separate data-migration
step needed before the new endpoints go live.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'n4o5p6q7r8s9'
down_revision: Union[str, Sequence[str], None] = '6c5d9da5ce73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'breathquest_parent_children',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('breathquest_parents.id'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('breathquest_patients.id'), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('parent_id', 'patient_id', name='uq_parent_child'),
    )
    op.create_index('ix_breathquest_parent_children_parent_id', 'breathquest_parent_children', ['parent_id'])
    op.create_index('ix_breathquest_parent_children_patient_id', 'breathquest_parent_children', ['patient_id'])

    # Backfill: every existing Parent row already has exactly one child via
    # patient_id (nullable=False on that column always required it) --
    # give each one a matching primary link so nothing needs a fresh
    # "add child" action just to see the child they already had. UUIDs are
    # generated in Python (uuid4), not via a Postgres gen_random_uuid()
    # call, since this project doesn't otherwise depend on the pgcrypto
    # extension being enabled.
    import uuid as _uuid
    connection = op.get_bind()
    parent_children = sa.table(
        'breathquest_parent_children',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('parent_id', postgresql.UUID(as_uuid=True)),
        sa.column('patient_id', postgresql.UUID(as_uuid=True)),
        sa.column('is_primary', sa.Boolean()),
    )
    parents = sa.table(
        'breathquest_parents',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('patient_id', postgresql.UUID(as_uuid=True)),
    )
    existing = connection.execute(sa.select(parents.c.id, parents.c.patient_id).where(parents.c.patient_id.isnot(None))).fetchall()
    if existing:
        connection.execute(
            parent_children.insert(),
            [{'id': _uuid.uuid4(), 'parent_id': row.id, 'patient_id': row.patient_id, 'is_primary': True} for row in existing],
        )


def downgrade() -> None:
    op.drop_index('ix_breathquest_parent_children_patient_id', table_name='breathquest_parent_children')
    op.drop_index('ix_breathquest_parent_children_parent_id', table_name='breathquest_parent_children')
    op.drop_table('breathquest_parent_children')
