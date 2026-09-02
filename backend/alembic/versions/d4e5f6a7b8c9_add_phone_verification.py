"""add phone verification table and parent_phone consent columns

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-12

Backs breathquest_core/parental_consent.py's phone factor -- now required
alongside email (both, not either) on POST /auth/kid-register:
  - breathquest_phone_verifications, a new table mirroring
    breathquest_email_verifications exactly (see models/breathquest_models.py's
    PhoneVerification for why this is a separate table rather than a
    column bolted onto EmailVerification)
  - breathquest_patients.parent_phone / parent_phone_consent_verified_at,
    recording which phone consented and when, same shape as the existing
    parent_email / parent_consent_verified_at pair

Chains on c3d4e5f6a7b8 (the COPPA email-consent columns), the real
current head on main as of this migration.

Hand-written, same reasoning as the prior three migrations: no live DB in
this sandbox to autogenerate against.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Already present in the baseline schema.
    pass


def downgrade() -> None:
    # Owned by the baseline schema.
    pass