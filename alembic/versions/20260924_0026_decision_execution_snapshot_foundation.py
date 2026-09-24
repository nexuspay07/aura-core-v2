"""preserve canonical Decision execution snapshots"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = "20260924_0026"
down_revision = "20260924_0025"
branch_labels = None
depends_on = None

def _recreate_mode():
    return "always" if op.get_bind().dialect.name == "sqlite" else "auto"

def upgrade():
    op.create_table(
        "decision_execution_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("intelligence_session_id", sa.Integer(), sa.ForeignKey("intelligence_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("snapshot_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("canonical_decision_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("public_id", name="uq_decision_execution_snapshots_public_id"),
        sa.UniqueConstraint("intelligence_session_id", "snapshot_version", name="uq_decision_execution_snapshots_session_version"),
        sa.CheckConstraint("length(trim(public_id)) > 0", name="ck_decision_execution_snapshots_public_id_nonempty"),
        sa.CheckConstraint("snapshot_version > 0", name="ck_decision_execution_snapshots_version_positive"),
        sa.CheckConstraint("snapshot_schema_version > 0", name="ck_decision_execution_snapshots_schema_version_positive"),
    )
    op.create_index("ix_decision_execution_snapshots_scope_session", "decision_execution_snapshots", ["user_id", "organization_id", "workspace_id", "intelligence_session_id"])

    with op.batch_alter_table("personal_decisions", recreate=_recreate_mode()) as batch:
        batch.add_column(sa.Column("public_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("canonical_snapshot_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_personal_decisions_canonical_snapshot", "decision_execution_snapshots", ["canonical_snapshot_id"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_personal_decisions_public_id", ["public_id"])
        batch.create_unique_constraint("uq_personal_decisions_canonical_snapshot", ["canonical_snapshot_id"])
        batch.create_check_constraint("ck_personal_decisions_public_id_nonempty", "length(trim(public_id)) > 0")
        batch.create_index("ix_personal_decisions_canonical_snapshot", ["canonical_snapshot_id"])
    bind = op.get_bind()
    ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM personal_decisions")).fetchall()]
    generated = [str(uuid4()) for _ in ids]
    if len(set(generated)) != len(generated):
        raise RuntimeError("Personal Decision UUID backfill collision")
    for decision_id, public_id in zip(ids, generated):
        bind.execute(sa.text("UPDATE personal_decisions SET public_id=:public_id WHERE id=:id"), {"public_id": public_id, "id": decision_id})
    with op.batch_alter_table("personal_decisions", recreate=_recreate_mode()) as batch:
        batch.alter_column("public_id", existing_type=sa.String(36), nullable=False)

    with op.batch_alter_table("strategy_revisions", recreate=_recreate_mode()) as batch:
        batch.drop_constraint("ck_strategy_revisions_direct_source_decision", type_="check")
        batch.add_column(sa.Column("source_decision_snapshot_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_strategy_revisions_source_decision_snapshot", "decision_execution_snapshots", ["source_decision_snapshot_id"], ["id"], ondelete="RESTRICT")
        batch.create_check_constraint("ck_strategy_revisions_direct_source_decision", "origin_type = 'decision_derived' OR (source_decision_id IS NULL AND source_decision_snapshot_id IS NULL)")
        batch.create_index("ix_strategy_revisions_source_decision_snapshot", ["source_decision_snapshot_id"])

    with op.batch_alter_table("strategy_create_idempotency", recreate=_recreate_mode()) as batch:
        batch.drop_constraint("ck_strategy_create_idempotency_operation", type_="check")
        batch.create_check_constraint("ck_strategy_create_idempotency_operation", "operation IN ('strategy_create_direct', 'strategy_create_from_decision')")

def downgrade():
    with op.batch_alter_table("strategy_create_idempotency", recreate=_recreate_mode()) as batch:
        batch.drop_constraint("ck_strategy_create_idempotency_operation", type_="check")
        batch.create_check_constraint("ck_strategy_create_idempotency_operation", "operation = 'strategy_create_direct'")
    with op.batch_alter_table("strategy_revisions", recreate=_recreate_mode()) as batch:
        batch.drop_index("ix_strategy_revisions_source_decision_snapshot")
        batch.drop_constraint("ck_strategy_revisions_direct_source_decision", type_="check")
        batch.drop_constraint("fk_strategy_revisions_source_decision_snapshot", type_="foreignkey")
        batch.drop_column("source_decision_snapshot_id")
        batch.create_check_constraint("ck_strategy_revisions_direct_source_decision", "origin_type = 'decision_derived' OR source_decision_id IS NULL")
    with op.batch_alter_table("personal_decisions", recreate=_recreate_mode()) as batch:
        batch.drop_index("ix_personal_decisions_canonical_snapshot")
        batch.drop_constraint("uq_personal_decisions_canonical_snapshot", type_="unique")
        batch.drop_constraint("uq_personal_decisions_public_id", type_="unique")
        batch.drop_constraint("ck_personal_decisions_public_id_nonempty", type_="check")
        batch.drop_constraint("fk_personal_decisions_canonical_snapshot", type_="foreignkey")
        batch.drop_column("canonical_snapshot_id")
        batch.drop_column("public_id")
    op.drop_table("decision_execution_snapshots")
