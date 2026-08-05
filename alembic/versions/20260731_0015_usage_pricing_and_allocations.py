"""add usage pricing and immutable invoice usage allocations

Revision ID: 20260731_0015
Revises: 20260730_0014
"""
from alembic import op
import sqlalchemy as sa


revision = "20260731_0015"
down_revision = "20260730_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usage_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("feature_key", sa.String(length=128), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit_price >= 0", name="ck_usage_prices_unit_price_nonnegative"),
        sa.CheckConstraint("effective_until IS NULL OR effective_until > effective_from", name="ck_usage_prices_effective_period"),
    )
    for name, column in (("ix_usage_prices_organization_id", "organization_id"), ("ix_usage_prices_plan_id", "plan_id"), ("ix_usage_prices_feature_key", "feature_key"), ("ix_usage_prices_effective_from", "effective_from"), ("ix_usage_prices_effective_until", "effective_until"), ("ix_usage_prices_is_active", "is_active")):
        op.create_index(name, "usage_prices", [column])
    op.create_table(
        "invoice_usage_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("usage_record_id", sa.Integer(), sa.ForeignKey("usage_records.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("invoice_line_item_id", sa.Integer(), sa.ForeignKey("invoice_line_items.id"), nullable=False),
        sa.Column("quantity_allocated", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("usage_record_id", name="uq_invoice_usage_allocations_usage_record"),
        sa.CheckConstraint("quantity_allocated > 0", name="ck_invoice_usage_allocations_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_invoice_usage_allocations_unit_price_nonnegative"),
        sa.CheckConstraint("amount >= 0", name="ck_invoice_usage_allocations_amount_nonnegative"),
    )
    for name, column in (("ix_invoice_usage_allocations_organization_id", "organization_id"), ("ix_invoice_usage_allocations_usage_record_id", "usage_record_id"), ("ix_invoice_usage_allocations_invoice_id", "invoice_id"), ("ix_invoice_usage_allocations_invoice_line_item_id", "invoice_line_item_id")):
        op.create_index(name, "invoice_usage_allocations", [column])


def downgrade():
    op.drop_table("invoice_usage_allocations")
    op.drop_table("usage_prices")
