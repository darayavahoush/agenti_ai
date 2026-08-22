"""
models/therapist.py — Assessment-native therapist accounts.

Distinct from the retiring app.models.breathquest_models.Therapist (see
main.py's 2026-08-07 disable notes) -- this is the real, going-forward
therapist identity for agenti_ai/Assessment, not tied to BreathQuest.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Therapist(Base):
    __tablename__ = "therapists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    # Nullable as of 2026-08-22: a Google-only account (google_sub set,
    # never set a password) has nothing to put here. verify_password is
    # never called for such an account -- login_therapist's password
    # branch and google_login_or_register's branch are mutually
    # exclusive per-request, not merged.
    hashed_password = Column(String, nullable=True)
    full_name = Column(String, nullable=False)
    clinic_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    # Added 2026-08-11 for the agenti_ai <-> quest-games identity merge --
    # quest-games' now-retired Therapist model tracked this; this is the
    # one field it had that Assessment's canonical Therapist didn't.
    last_login = Column(TIMESTAMP, nullable=True)
    # Added 2026-08-13: collected on signup, not verified (no SMS provider
    # wired up yet -- see breathquest_core/phone_provider.py's kid-consent
    # path for the one place phone verification does exist). Nullable
    # since existing accounts predate this field.
    phone = Column(String, nullable=True)
    # Added 2026-08-22 for Google Sign-In. Google's stable per-account
    # identifier ("sub" claim) -- not the email, since a user could
    # change their Google account's email later and we want the link to
    # survive that. Nullable/unique: most rows won't have one (password
    # accounts that never linked Google), but any row that does must be
    # unique so a Google identity can't front two different therapists.
    google_sub = Column(String, nullable=True, unique=True, index=True)
