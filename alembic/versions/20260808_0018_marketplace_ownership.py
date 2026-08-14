"""add durable marketplace ownership metadata

Revision ID: 20260808_0018
Revises: 20260807_0017
"""
from alembic import op
import sqlalchemy as sa

revision = "20260808_0018"
down_revision = "20260807_0017"
branch_labels = None
depends_on = None

_columns = (
    ("owner_user_id", sa.Integer()), ("organization_id", sa.Integer()),
    ("workspace_id", sa.Integer()), ("description", sa.String()),
    ("category", sa.String(32)), ("item_type", sa.String(32)),
    ("created_at", sa.String()), ("updated_at", sa.String()),
)

def upgrade():
    existing = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("strategies")}
    for name, column_type in _columns:
        if name not in existing:
            op.add_column("strategies", sa.Column(name, column_type, nullable=True))
    for name in ("owner_user_id", "organization_id", "workspace_id"):
        index = f"ix_strategies_{name}"
        if index not in {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("strategies")}:
            op.create_index(index, "strategies", [name])

def downgrade():
    # Preserve legacy strategy content; only drop the metadata introduced here.
    with op.batch_alter_table("strategies") as batch:
        for name in ("owner_user_id", "organization_id", "workspace_id"):
            batch.drop_index(f"ix_strategies_{name}")
        for name, _ in reversed(_columns):
            batch.drop_column(name)
