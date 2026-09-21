"""add content-free Control Center intelligence telemetry fields"""
from alembic import op
import sqlalchemy as sa

revision = "20260921_0023"
down_revision = "20260815_0022"
branch_labels = None
depends_on = None

def upgrade():
    for column in (
        sa.Column("request_id", sa.String(length=36), nullable=True), sa.Column("route", sa.String(length=100), nullable=True),
        sa.Column("request_mode", sa.String(length=64), nullable=True), sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True), sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True), sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True), sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=True), sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("provider_call_count", sa.Integer(), nullable=True),
    ):
        op.add_column("usage_logs", column)
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_usage_logs_session_id", "usage_logs", "intelligence_sessions", ["session_id"], ["id"])
    for name, columns, unique in (
        ("ix_usage_logs_request_id", ["request_id"], True), ("ix_usage_logs_route", ["route"], False),
        ("ix_usage_logs_outcome", ["outcome"], False), ("ix_usage_logs_session_id", ["session_id"], False),
        ("ix_usage_logs_created_at", ["created_at"], False),
    ):
        op.create_index(name, "usage_logs", columns, unique=unique)

def downgrade():
    for name in ("ix_usage_logs_created_at", "ix_usage_logs_session_id", "ix_usage_logs_outcome", "ix_usage_logs_route", "ix_usage_logs_request_id"):
        op.drop_index(name, table_name="usage_logs")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_usage_logs_session_id", "usage_logs", type_="foreignkey")
    for name in ("provider_call_count", "retry_count", "provider_latency_ms", "reasoning_tokens", "output_tokens", "input_tokens", "session_id", "provider", "error_category", "outcome", "request_mode", "route", "request_id"):
        op.drop_column("usage_logs", name)
