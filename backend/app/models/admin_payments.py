from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from app.database import Base

def _now():
    return datetime.now(timezone.utc)

class AuthEvent(Base):
    __tablename__ = "auth_events"
    id = Column(Integer, primary_key=True)
    user_type = Column(String(16), nullable=False, index=True)  # kid | parent | therapist | admin
    user_id = Column(String(64), index=True)
    success = Column(Boolean, nullable=False)
    ip = Column(String(64))
    user_agent = Column(String(256))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    merchant_order_id = Column(String(64), nullable=False, unique=True, index=True)
    phonepe_order_id = Column(String(64))
    owner_kind = Column(String(16), nullable=False)  # parent | therapist
    owner_id = Column(String(64), nullable=False, index=True)
    plan_type = Column(String(32), nullable=False)
    amount_paise = Column(Integer, nullable=False)
    state = Column(String(16), nullable=False, default="created", index=True)  # created|pending|completed|failed
    payment_mode = Column(String(32))
    failure_reason = Column(String(256))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    completed_at = Column(DateTime(timezone=True))

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

class AiSummary(Base):
    __tablename__ = "ai_summaries"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    input_numbers = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
