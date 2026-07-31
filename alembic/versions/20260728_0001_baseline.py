"""Aura baseline schema; non-destructive for existing SQLite development databases."""
from alembic import op
from app.db.baseline_schema import target_metadata
revision = "20260728_0001"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    bind = op.get_bind()
    for metadata in target_metadata:
        metadata.create_all(bind=bind, tables=[table for table in metadata.sorted_tables if table.name not in {"plans", "plan_features"}], checkfirst=True)
def downgrade():
    raise RuntimeError("Baseline downgrade is intentionally disabled to protect existing data.")
