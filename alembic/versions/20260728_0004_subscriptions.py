"""Add the canonical subscriptions aggregate."""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0004"
down_revision = "20260728_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("billing_cycle", sa.String(16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("renews_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("external_reference", sa.String(255)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending','trialing','active','past_due','paused','cancelled','expired')", name="ck_subscriptions_status"),
        sa.CheckConstraint("billing_cycle IN ('monthly','annual','custom')", name="ck_subscriptions_billing_cycle"),
        sa.CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="ck_subscriptions_ends_after_start"),
        sa.CheckConstraint("renews_at IS NULL OR renews_at >= starts_at", name="ck_subscriptions_renews_after_start"),
        sa.CheckConstraint("cancelled_at IS NULL OR cancelled_at >= starts_at", name="ck_subscriptions_cancelled_after_start"),
        sa.CheckConstraint("trial_ends_at IS NULL OR trial_ends_at >= starts_at", name="ck_subscriptions_trial_after_start"),
        sa.CheckConstraint("trial_ends_at IS NULL OR ends_at IS NULL OR trial_ends_at <= ends_at", name="ck_subscriptions_trial_before_end"),
        sa.CheckConstraint("version > 0", name="ck_subscriptions_version_positive"),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_billing_cycle", "subscriptions", ["billing_cycle"])
    op.create_index("ix_subscriptions_external_reference", "subscriptions", ["external_reference"])
    op.create_index("ix_subscriptions_organization_status", "subscriptions", ["organization_id", "status"])


def downgrade():
    op.drop_index("ix_subscriptions_organization_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_external_reference", table_name="subscriptions")
    op.drop_index("ix_subscriptions_billing_cycle", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_organization_id", table_name="subscriptions")
    op.drop_table("subscriptions")
