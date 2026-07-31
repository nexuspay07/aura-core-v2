"""Add the append-only commercial usage ledger."""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0006"
down_revision = "20260728_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("feature_key", sa.String(128), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("source_type", sa.String(16)),
        sa.Column("source_id", sa.String(255)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_usage_records_organization_idempotency"),
        sa.CheckConstraint("quantity > 0", name="ck_usage_records_quantity_positive"),
        sa.CheckConstraint("source_type IS NULL OR source_type IN ('api','system','workspace','user')", name="ck_usage_records_source_type"),
    )
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"])
    op.create_index("ix_usage_records_subscription_id", "usage_records", ["subscription_id"])
    op.create_index("ix_usage_records_feature_key", "usage_records", ["feature_key"])
    op.create_index("ix_usage_records_occurred_at", "usage_records", ["occurred_at"])
    op.create_index("ix_usage_records_organization_feature_occurred", "usage_records", ["organization_id", "feature_key", "occurred_at"])
    op.create_index("ix_usage_records_idempotency_key", "usage_records", ["idempotency_key"])


def downgrade():
    op.drop_index("ix_usage_records_idempotency_key", table_name="usage_records")
    op.drop_index("ix_usage_records_organization_feature_occurred", table_name="usage_records")
    op.drop_index("ix_usage_records_occurred_at", table_name="usage_records")
    op.drop_index("ix_usage_records_feature_key", table_name="usage_records")
    op.drop_index("ix_usage_records_subscription_id", table_name="usage_records")
    op.drop_index("ix_usage_records_organization_id", table_name="usage_records")
    op.drop_table("usage_records")
