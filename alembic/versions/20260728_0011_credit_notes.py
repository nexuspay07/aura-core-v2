from alembic import op
import sqlalchemy as sa


revision = "20260728_0011"
down_revision = "20260728_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "credit_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("credit_note_number", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason", sa.String(512)),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_applied", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("amount_remaining", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("organization_id", "credit_note_number", name="uq_credit_notes_organization_number"),
        sa.CheckConstraint("status IN ('draft','issued','fully_applied','void')", name="ck_credit_notes_status"),
        sa.CheckConstraint("subtotal >= 0", name="ck_credit_notes_subtotal_nonnegative"),
        sa.CheckConstraint("tax >= 0", name="ck_credit_notes_tax_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_credit_notes_total_nonnegative"),
        sa.CheckConstraint("amount_applied >= 0", name="ck_credit_notes_applied_nonnegative"),
        sa.CheckConstraint("amount_remaining >= 0", name="ck_credit_notes_remaining_nonnegative"),
        sa.CheckConstraint("amount_applied <= total", name="ck_credit_notes_applied_not_over_total"),
        sa.CheckConstraint("amount_remaining <= total", name="ck_credit_notes_remaining_not_over_total"),
        sa.CheckConstraint("amount_applied + amount_remaining <= total", name="ck_credit_notes_balance_not_over_total"),
        sa.CheckConstraint("version > 0", name="ck_credit_notes_version"),
    )
    for name, columns in (
        ("ix_credit_notes_organization_id", ["organization_id"]),
        ("ix_credit_notes_invoice_id", ["invoice_id"]),
        ("ix_credit_notes_status", ["status"]),
    ):
        op.create_index(name, "credit_notes", columns)

    op.create_table(
        "credit_note_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("credit_note_id", sa.Integer(), sa.ForeignKey("credit_notes.id"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax", sa.Numeric(18, 4), nullable=False),
        sa.Column("total", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("credit_note_id", "line_number", name="uq_credit_note_lines_number"),
        sa.CheckConstraint("line_number > 0", name="ck_credit_note_lines_number_positive"),
        sa.CheckConstraint("quantity >= 0", name="ck_credit_note_lines_quantity_nonnegative"),
    )
    op.create_index("ix_credit_note_line_items_credit_note_id", "credit_note_line_items", ["credit_note_id"])


def downgrade():
    op.drop_table("credit_note_line_items")
    op.drop_table("credit_notes")
