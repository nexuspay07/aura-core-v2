"""add durable Strategy create idempotency"""

from alembic import op
import sqlalchemy as sa


revision = "20260924_0025"
down_revision = "20260923_0024"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategy_create_idempotency",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("claim_token", sa.String(length=36), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("strategy_resource_id", sa.Integer(), sa.ForeignKey("strategy_resources.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(trim(idempotency_key)) > 0", name="ck_strategy_create_idempotency_key_nonempty"),
        sa.CheckConstraint("length(request_fingerprint) = 64", name="ck_strategy_create_idempotency_fingerprint"),
        sa.CheckConstraint("operation = 'strategy_create_direct'", name="ck_strategy_create_idempotency_operation"),
        sa.CheckConstraint("status IN ('in_progress', 'completed')", name="ck_strategy_create_idempotency_status"),
        sa.CheckConstraint("(owner_user_id IS NOT NULL AND organization_id IS NULL AND workspace_id IS NULL) OR (owner_user_id IS NULL AND organization_id IS NOT NULL AND workspace_id IS NOT NULL)", name="ck_strategy_create_idempotency_tenancy_shape"),
        sa.CheckConstraint("(status = 'in_progress' AND strategy_resource_id IS NULL AND claim_token IS NOT NULL AND lease_expires_at IS NOT NULL) OR (status = 'completed' AND strategy_resource_id IS NOT NULL AND claim_token IS NULL AND lease_expires_at IS NULL)", name="ck_strategy_create_idempotency_state"),
    )
    personal = sa.text("owner_user_id IS NOT NULL")
    workspace = sa.text("workspace_id IS NOT NULL")
    op.create_index("uq_strategy_create_idempotency_personal_key", "strategy_create_idempotency", ["actor_user_id", "owner_user_id", "operation", "idempotency_key"], unique=True, postgresql_where=personal, sqlite_where=personal)
    op.create_index("uq_strategy_create_idempotency_workspace_key", "strategy_create_idempotency", ["actor_user_id", "organization_id", "workspace_id", "operation", "idempotency_key"], unique=True, postgresql_where=workspace, sqlite_where=workspace)
    op.create_index("ix_strategy_create_idempotency_resource", "strategy_create_idempotency", ["strategy_resource_id"])
    op.create_index("ix_strategy_create_idempotency_status_lease", "strategy_create_idempotency", ["status", "lease_expires_at"])


def downgrade():
    op.drop_table("strategy_create_idempotency")
