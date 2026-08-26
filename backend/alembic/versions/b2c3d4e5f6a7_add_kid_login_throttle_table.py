"""add breathquest_kid_login_throttle table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-12

Backs breathquest_core/login_throttle.py's brute-force protection for
POST /auth/kid-login. A new table, not an ALTER on an existing one, so
unlike a1b2c3d4e5f6 this one is safe even if create_all() runs first --
create_all() only ever skips tables that already exist, and this is a
genuinely new one. Included as an explicit Alembic migration anyway
(rather than left to create_all()) to keep a single source of truth for
schema history going forward, per the standing note in main.py.

Hand-written, same reasoning as a1b2c3d4e5f6: no live DB in this sandbox
to autogenerate against.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This table is already part of the 000baseline0 baseline schema.
    pass


def downgrade() -> None:
    # This table belongs to the baseline schema and must not be removed
    # by this migration.
    pass
