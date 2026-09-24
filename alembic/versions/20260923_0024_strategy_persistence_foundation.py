"""add canonical Strategy persistence foundation"""

from alembic import op
import sqlalchemy as sa


revision = "20260923_0024"
down_revision = "20260921_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "strategy_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("current_revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_strategy_resources_public_id"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_strategy_resources_title_nonempty"),
        sa.CheckConstraint("current_revision_number > 0", name="ck_strategy_resources_current_revision_positive"),
        sa.CheckConstraint("lock_version > 0", name="ck_strategy_resources_lock_version_positive"),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND organization_id IS NULL AND workspace_id IS NULL) OR "
            "(owner_user_id IS NULL AND organization_id IS NOT NULL AND workspace_id IS NOT NULL)",
            name="ck_strategy_resources_tenancy_shape",
        ),
    )
    op.create_index("ix_strategy_resources_owner_archive_updated", "strategy_resources", ["owner_user_id", "archived_at", "updated_at"])
    op.create_index("ix_strategy_resources_workspace_archive_updated", "strategy_resources", ["organization_id", "workspace_id", "archived_at", "updated_at"])
    op.create_index("ix_strategy_resources_created_by", "strategy_resources", ["created_by_user_id"])

    op.create_table(
        "strategy_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategy_resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("canonical_result_json", sa.JSON(), nullable=False),
        sa.Column("snapshot_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("origin_type", sa.String(length=32), nullable=False),
        sa.Column("source_decision_id", sa.Integer(), sa.ForeignKey("personal_decisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("strategy_id", "revision_number", name="uq_strategy_revisions_strategy_revision"),
        sa.CheckConstraint("revision_number > 0", name="ck_strategy_revisions_revision_positive"),
        sa.CheckConstraint("snapshot_schema_version > 0", name="ck_strategy_revisions_snapshot_schema_version_positive"),
        sa.CheckConstraint("origin_type IN ('direct', 'decision_derived')", name="ck_strategy_revisions_origin_type"),
        sa.CheckConstraint("origin_type = 'decision_derived' OR source_decision_id IS NULL", name="ck_strategy_revisions_direct_source_decision"),
    )
    op.create_index("ix_strategy_revisions_strategy_created", "strategy_revisions", ["strategy_id", "created_at"])
    op.create_index("ix_strategy_revisions_source_decision", "strategy_revisions", ["source_decision_id"])


def downgrade():
    op.drop_table("strategy_revisions")
    op.drop_table("strategy_resources")
