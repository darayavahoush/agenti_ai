"""add overdue value to assignmentstatus enum

Revision ID: h8i9j0k1l2m3
Revises: c68c74ae64cd
Create Date: 2026-09-10

The breathquest_assignments table's `status` column is declared in Python
(AssignmentStatus in breathquest_models.py) with values
assigned/in_progress/completed/overdue -- but the baseline migration
accidentally reused the Postgres enum type name `assignmentstatus` for
BOTH this table and an older, unrelated VaakMirror exercise-assignments
table (which has not_started/assigned/in_progress/completed, no overdue).
Since both columns share one Postgres enum type by name, only the first
table's value list actually got created in the database -- leaving
`overdue` missing from the live enum even though breathquest_assignments'
Python model has always declared it. Querying/writing status='overdue'
against breathquest_assignments has been failing with
InvalidTextRepresentationError as a result (see dashboard.py's
list_patient_alerts -- this is what broke the therapist dashboard's
alerts load).

This adds the missing value to the existing shared enum type. Safe and
non-destructive: Postgres enum types can carry values a given table never
uses, so this has zero effect on the other (VaakMirror) table that shares
this type name.

Longer-term this shared-name collision between two logically distinct
enums is worth splitting into two separately-named Postgres types, but
that requires a more invasive migration (new type, column swap, drop old
type) -- out of scope for this fix, which just unblocks the live 500.
"""
from alembic import op

revision = 'h8i9j0k1l2m3'
down_revision = 'c68c74ae64cd'
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE historically cannot run inside a
    # transaction block in Postgres (pre-12 always, and even on 12+ a
    # newly added value can't be used in the SAME transaction that added
    # it). Alembic wraps migrations in a transaction by default, so this
    # runs in an explicit autocommit block instead to sidestep both
    # issues regardless of server version. IF NOT EXISTS makes it safe
    # to re-run if it ever partially applies.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE assignmentstatus ADD VALUE IF NOT EXISTS 'overdue'")


def downgrade():
    # Postgres has no native "remove enum value" -- downgrading this
    # cleanly would require rebuilding the type (create new type without
    # the value, migrate the column, drop old type), which risks data
    # loss if any row is actually using 'overdue' by that point. Left as
    # a no-op rather than a lossy/destructive downgrade.
    pass
