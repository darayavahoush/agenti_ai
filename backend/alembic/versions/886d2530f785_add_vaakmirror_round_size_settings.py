"""add vaakmirror_round_size_settings

Revision ID: 886d2530f785
Revises: acbe12154469
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "886d2530f785"
down_revision = "acbe12154469"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vaakmirror_round_size_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column(
            "game",
            postgresql.ENUM("mirror_mirror", "tongue_tamer", "lip_sync_hero", name="gamename", create_type=False),
            nullable=False,
        ),
        sa.Column("round_size", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_vaakmirror_round_size_settings_patient_id",
        "vaakmirror_round_size_settings", ["patient_id"],
    )
    op.create_unique_constraint(
        "uq_round_size_patient_game", "vaakmirror_round_size_settings", ["patient_id", "game"],
    )


def downgrade():
    op.drop_constraint("uq_round_size_patient_game", "vaakmirror_round_size_settings", type_="unique")
    op.drop_index("ix_vaakmirror_round_size_settings_patient_id", table_name="vaakmirror_round_size_settings")
    op.drop_table("vaakmirror_round_size_settings")
