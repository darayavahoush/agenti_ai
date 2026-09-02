"""add shape calibration and labeling fields to attempts

Revision ID: c68c74ae64cd
Revises: 71ec5364b35a
Create Date: 2026-09-02 15:35:41.263106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c68c74ae64cd'
down_revision: Union[str, Sequence[str], None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


attempt_label_enum = sa.Enum("correct", "incorrect", name="attemptlabel")


def upgrade() -> None:
    """Upgrade schema."""
    attempt_label_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("attempts", sa.Column("shape", sa.String(length=32), nullable=True))
    op.add_column("attempts", sa.Column("openness", sa.Float(), nullable=True))
    op.add_column("attempts", sa.Column("spread", sa.Float(), nullable=True))
    op.add_column("attempts", sa.Column("predicted_tier", sa.String(length=8), nullable=True))
    op.add_column("attempts", sa.Column("therapist_label", attempt_label_enum, nullable=True))
    op.add_column("attempts", sa.Column("labeled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("attempts", sa.Column("labeled_by", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("attempts", "labeled_by")
    op.drop_column("attempts", "labeled_at")
    op.drop_column("attempts", "therapist_label")
    op.drop_column("attempts", "predicted_tier")
    op.drop_column("attempts", "spread")
    op.drop_column("attempts", "openness")
    op.drop_column("attempts", "shape")
    attempt_label_enum.drop(op.get_bind(), checkfirst=True)
