"""add durable payment ledger

Revision ID: 20260731_0016
Revises: 20260731_0015
"""
from alembic import op
import sqlalchemy as sa

revision = "20260731_0016"
down_revision = "20260731_0015"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("payment_attempt_id", sa.Integer(), sa.ForeignKey("payment_attempts.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("payment_attempt_id", name="uq_payments_attempt"),
        sa.UniqueConstraint("provider", "provider_reference", name="uq_payments_provider_reference"),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )
    for name, column in (("ix_payments_organization_id", "organization_id"), ("ix_payments_invoice_id", "invoice_id"), ("ix_payments_payment_attempt_id", "payment_attempt_id"), ("ix_payments_provider", "provider"), ("ix_payments_paid_at", "paid_at")):
        op.create_index(name, "payments", [column])

def downgrade():
    op.drop_table("payments")
