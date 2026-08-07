"""add organization account types and server-controlled active workspace

Revision ID: 20260807_0017
Revises: 20260731_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260807_0017"
down_revision = "20260731_0016"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite cannot add a check constraint in place, so batch mode rebuilds the
    # table while preserving existing data.  The server default backfills every
    # legacy organization before future writes are required to supply a value.
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_type",
                sa.String(length=20),
                nullable=False,
                server_default="business",
            )
        )
        batch_op.create_check_constraint(
            "ck_organizations_account_type",
            "account_type IN ('personal', 'business', 'enterprise')",
        )
        batch_op.create_index("ix_organizations_account_type", ["account_type"])

    # A nullable, post-creation foreign key is safe despite the existing
    # workspaces.created_by_user_id -> users.id relationship.  Batch mode gives
    # SQLite the same FK semantics as PostgreSQL.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("active_workspace_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_users_active_workspace_id",
            "workspaces",
            ["active_workspace_id"],
            ["id"],
        )
        batch_op.create_index("ix_users_active_workspace_id", ["active_workspace_id"])


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_active_workspace_id")
        batch_op.drop_constraint("fk_users_active_workspace_id", type_="foreignkey")
        batch_op.drop_column("active_workspace_id")

    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_index("ix_organizations_account_type")
        batch_op.drop_constraint("ck_organizations_account_type", type_="check")
        batch_op.drop_column("account_type")
