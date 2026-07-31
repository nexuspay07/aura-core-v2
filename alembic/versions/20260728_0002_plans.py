"""Add canonical commercial plans aggregate."""
from alembic import op
import sqlalchemy as sa
revision = "20260728_0002"
down_revision = "20260728_0001"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("plans", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(128), nullable=False), sa.Column("seat_limit", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("code", name="uq_plans_code"), sa.CheckConstraint("seat_limit >= 0", name="ck_plans_seat_limit"))
    op.create_index("ix_plans_code", "plans", ["code"]); op.create_index("ix_plans_is_active", "plans", ["is_active"])
def downgrade():
    op.drop_table("plans")
