"""enforce one saved Personal Decision per Ask session

Revision ID: 20260811_0021
Revises: 20260810_0020
"""

from alembic import op


revision = "20260811_0021"
down_revision = "20260810_0020"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("personal_decisions") as batch:
        batch.create_unique_constraint("uq_personal_decisions_source_session", ["source_session_id"])


def downgrade():
    with op.batch_alter_table("personal_decisions") as batch:
        batch.drop_constraint("uq_personal_decisions_source_session", type_="unique")
