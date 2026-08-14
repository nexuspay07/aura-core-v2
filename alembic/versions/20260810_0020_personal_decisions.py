"""add Personal Decision product records

Revision ID: 20260810_0020
Revises: 20260809_0019
"""
from alembic import op
import sqlalchemy as sa

revision = "20260810_0020"
down_revision = "20260809_0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "personal_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_session_id", sa.Integer(), sa.ForeignKey("intelligence_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_question", sa.Text(), nullable=False),
        sa.Column("decision_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("related_goal_id", sa.Integer(), nullable=True),
        sa.Column("analysis_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("confidence_rationale", sa.Text(), nullable=True),
        sa.Column("user_choice", sa.Text(), nullable=True),
        sa.Column("user_choice_rationale", sa.Text(), nullable=True),
        sa.Column("decision_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome_status", sa.String(32), nullable=False, server_default="not_recorded"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open','decided','awaiting_outcome','completed')", name="ck_personal_decisions_status"),
        sa.CheckConstraint("outcome_status IN ('not_recorded','pending','recorded')", name="ck_personal_decisions_outcome_status"),
    )
    op.create_index("ix_personal_decisions_scope_updated", "personal_decisions", ["organization_id", "workspace_id", "user_id", "updated_at"])
    op.create_index("ix_personal_decisions_scope_status", "personal_decisions", ["organization_id", "workspace_id", "status"])
    op.create_index("ix_personal_decisions_review_date", "personal_decisions", ["review_date"])
    op.create_index("ix_personal_decisions_source_session", "personal_decisions", ["source_session_id"])


def downgrade():
    op.drop_table("personal_decisions")
