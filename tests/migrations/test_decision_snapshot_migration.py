from sqlalchemy import create_engine, inspect, text
from tests.migrations.helpers import downgrade, upgrade

def test_decision_snapshot_upgrade_backfill_constraints_and_downgrade(tmp_path):
    database = tmp_path / "decision-snapshot.db"
    upgrade(database, "20260924_0025")
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id,email,password_hash) VALUES (91,'historic@test','x')"))
        connection.execute(text("INSERT INTO organizations (id,name,slug,owner_user_id,account_type,plan,subscription_status,is_active) VALUES (91,'Historic','historic',91,'personal','free','inactive',1)"))
        connection.execute(text("INSERT INTO workspaces (id,organization_id,created_by_user_id,name,slug,workspace_type,is_active) VALUES (91,91,91,'Historic','historic','personal',1)"))
        connection.execute(text("INSERT INTO intelligence_sessions (id,organization_id,workspace_id,created_by_user_id,title,goal,session_type,status,is_active) VALUES (91,91,91,91,'Historic','Question','decision_analysis','completed',1)"))
        connection.execute(text("INSERT INTO personal_decisions (id,user_id,organization_id,workspace_id,source_session_id,title,original_question,decision_type,status,analysis_snapshot_json,recommendation,outcome_status) VALUES (91,91,91,91,91,'Historic','Question','general','open','{}','Answer','not_recorded')"))
    upgrade(database, "20260924_0026")
    inspector = inspect(engine)
    assert "decision_execution_snapshots" in inspector.get_table_names()
    with engine.connect() as connection:
        row = connection.execute(text("SELECT id,public_id,canonical_snapshot_id FROM personal_decisions WHERE id=91")).mappings().one()
        assert row["id"] == 91 and len(row["public_id"]) == 36 and row["canonical_snapshot_id"] is None
        connection.execute(text("INSERT INTO strategy_create_idempotency (id,idempotency_key,operation,request_fingerprint,actor_user_id,owner_user_id,status,claim_token,lease_expires_at) VALUES (91,'key','strategy_create_from_decision',:fingerprint,91,91,'in_progress','token','2030-01-01')"), {"fingerprint": "a" * 64})
    assert {item["name"] for item in inspector.get_indexes("strategy_revisions")} >= {"ix_strategy_revisions_source_decision_snapshot"}
    downgrade(database, "20260924_0025")
    assert "decision_execution_snapshots" not in inspect(engine).get_table_names()
