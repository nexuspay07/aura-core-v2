from alembic import op
import sqlalchemy as sa
revision="20260728_0010";down_revision="20260728_0009";branch_labels=None;depends_on=None
def upgrade():op.add_column("payment_attempts",sa.Column("reconciled_at",sa.DateTime(timezone=True)))
def downgrade():op.drop_column("payment_attempts","reconciled_at")
