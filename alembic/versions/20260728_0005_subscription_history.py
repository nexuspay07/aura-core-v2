"""Add append-only subscription history records."""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0005"
down_revision = "20260728_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscription_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("previous_status", sa.String(16)),
        sa.Column("new_status", sa.String(16)),
        sa.Column("previous_plan_id", sa.Integer(), sa.ForeignKey("plans.id")),
        sa.Column("new_plan_id", sa.Integer(), sa.ForeignKey("plans.id")),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(512)),
        sa.Column("actor_type", sa.String(16)),
        sa.Column("actor_id", sa.String(255)),
        sa.Column("external_reference", sa.String(255)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("event_type IN ('created','activated','trial_started','trial_ended','plan_changed','paused','resumed','cancelled','expired','renewed','payment_status_changed')", name="ck_subscription_history_event_type"),
        sa.CheckConstraint("previous_status IS NULL OR previous_status IN ('pending','trialing','active','past_due','paused','cancelled','expired')", name="ck_subscription_history_previous_status"),
        sa.CheckConstraint("new_status IS NULL OR new_status IN ('pending','trialing','active','past_due','paused','cancelled','expired')", name="ck_subscription_history_new_status"),
        sa.CheckConstraint("actor_type IS NULL OR actor_type IN ('system','user','organization','external')", name="ck_subscription_history_actor_type"),
        sa.CheckConstraint("event_type IN ('created','renewed','payment_status_changed') OR previous_status IS NOT NULL OR new_status IS NOT NULL OR previous_plan_id IS NOT NULL OR new_plan_id IS NOT NULL", name="ck_subscription_history_change_values"),
    )
    op.create_index("ix_subscription_history_subscription_id", "subscription_history", ["subscription_id"])
    op.create_index("ix_subscription_history_event_type", "subscription_history", ["event_type"])
    op.create_index("ix_subscription_history_effective_at", "subscription_history", ["effective_at"])
    op.create_index("ix_subscription_history_subscription_effective", "subscription_history", ["subscription_id", "effective_at"])
    op.create_index("ix_subscription_history_external_reference", "subscription_history", ["external_reference"])


def downgrade():
    op.drop_index("ix_subscription_history_external_reference", table_name="subscription_history")
    op.drop_index("ix_subscription_history_subscription_effective", table_name="subscription_history")
    op.drop_index("ix_subscription_history_effective_at", table_name="subscription_history")
    op.drop_index("ix_subscription_history_event_type", table_name="subscription_history")
    op.drop_index("ix_subscription_history_subscription_id", table_name="subscription_history")
    op.drop_table("subscription_history")
