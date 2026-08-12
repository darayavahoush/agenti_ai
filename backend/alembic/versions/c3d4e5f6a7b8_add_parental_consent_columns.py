"""add COPPA parental consent columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-12

Backs breathquest_core/parental_consent.py's gate on POST /auth/kid-register:
  - breathquest_email_verifications.verified_at, so a consent check can
    tell *when* an email was verified, not just whether it ever was
  - breathquest_patients.parent_email / parent_consent_verified_at, so a
    self-serve signup records which parent consented and when

Chains on b2c3d4e5f6a7 (the kid-login throttle table), the real current
head on main as of this migration -- both ALTERs on existing tables, so
unlike b2c3d4e5f6a7 this one is NOT safe to skip in favor of create_all():
if the app boots against a DB that's missing this migration, `alembic
upgrade head` must run before kid-register or verify/confirm will work.

Hand-written, same reasoning as a1b2c3d4e5f6 and b2c3d4e5f6a7: no live DB
in this sandbox to autogenerate against.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "breathquest_email_verifications",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "breathquest_patients",
        sa.Column("parent_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "breathquest_patients",
        sa.Column("parent_consent_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("breathquest_patients", "parent_consent_verified_at")
    op.drop_column("breathquest_patients", "parent_email")
    op.drop_column("breathquest_email_verifications", "verified_at")
