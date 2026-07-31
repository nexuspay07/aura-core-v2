"""add the ORM-declared payment attempt provider reference index

Revision ID: 20260730_0014
Revises: 20260728_0013
"""
from alembic import op

revision="20260730_0014"
down_revision="20260728_0013"
branch_labels=None
depends_on=None

def upgrade():
 op.create_index("ix_payment_attempts_provider_reference","payment_attempts",["provider_reference"])

def downgrade():
 op.drop_index("ix_payment_attempts_provider_reference",table_name="payment_attempts")
