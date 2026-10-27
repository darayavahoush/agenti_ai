"""admin dashboard tables: auth_events, payments, admin_users, ai_summaries"""
from alembic import op
import sqlalchemy as sa

revision = "a1d0c0de0001"
down_revision = "d3a5d17961ee"
branch_labels = None
depends_on = None

NOW = sa.text("now()")

def upgrade():
    op.create_table("auth_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_type", sa.String(16), nullable=False),
        sa.Column("user_id", sa.String(64)),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW))
    op.create_index("ix_auth_events_user_type", "auth_events", ["user_type"])
    op.create_index("ix_auth_events_user_id", "auth_events", ["user_id"])
    op.create_index("ix_auth_events_created_at", "auth_events", ["created_at"])
    op.create_table("payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("merchant_order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("phonepe_order_id", sa.String(64)),
        sa.Column("owner_kind", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False),
        sa.Column("plan_type", sa.String(32), nullable=False),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="created"),
        sa.Column("payment_mode", sa.String(32)),
        sa.Column("failure_reason", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_payments_merchant_order_id", "payments", ["merchant_order_id"])
    op.create_index("ix_payments_owner_id", "payments", ["owner_id"])
    op.create_index("ix_payments_state", "payments", ["state"])
    op.create_index("ix_payments_created_at", "payments", ["created_at"])
    op.create_table("admin_users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW))
    op.create_table("ai_summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("input_numbers", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW))
    op.create_index("ix_ai_summaries_created_at", "ai_summaries", ["created_at"])

def downgrade():
    op.drop_table("ai_summaries")
    op.drop_table("admin_users")
    op.drop_table("payments")
    op.drop_table("auth_events")
