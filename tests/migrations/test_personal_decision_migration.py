from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
import pytest

from tests.migrations.helpers import current, downgrade, upgrade


def test_personal_decision_migration_upgrade_downgrade_reupgrade_preserves_existing_tables(tmp_path):
    database = tmp_path / "personal-decisions.db"
    upgrade(database, "20260809_0019")
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email, password_hash) VALUES (1, 'person@test', 'x')"))
        connection.execute(text("INSERT INTO organizations (id, name, slug, owner_user_id, plan, subscription_status, is_active) VALUES (1, 'Personal Space', 'personal-migration', 1, 'free', 'inactive', 1)"))
        connection.execute(text("INSERT INTO workspaces (id, organization_id, created_by_user_id, name, slug, workspace_type, is_active) VALUES (1, 1, 1, 'My Workspace', 'my-workspace-migration', 'personal', 1)"))
        connection.execute(text("INSERT INTO intelligence_sessions (id, organization_id, workspace_id, created_by_user_id, title, goal, is_active) VALUES (1, 1, 1, 1, 'Source', 'Question', 1)"))
    upgrade(database, "20260811_0021")
    inspector = inspect(engine)
    assert "personal_decisions" in inspector.get_table_names()
    assert {"user_id", "organization_id", "workspace_id", "source_session_id", "analysis_snapshot_json", "status", "outcome_status", "review_date"} <= {column["name"] for column in inspector.get_columns("personal_decisions")}
    assert {"ix_personal_decisions_scope_updated", "ix_personal_decisions_scope_status", "ix_personal_decisions_review_date", "ix_personal_decisions_source_session"} <= {index["name"] for index in inspector.get_indexes("personal_decisions")}
    assert "uq_personal_decisions_source_session" in {constraint["name"] for constraint in inspector.get_unique_constraints("personal_decisions")}
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO personal_decisions (id, user_id, organization_id, workspace_id, source_session_id, title, original_question, decision_type, status, analysis_snapshot_json, recommendation, outcome_status) VALUES (1, 1, 1, 1, 1, 'Decision', 'Question', 'general', 'open', '{}', 'Review facts', 'not_recorded')"))
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("INSERT INTO personal_decisions (id, user_id, organization_id, workspace_id, source_session_id, title, original_question, decision_type, status, analysis_snapshot_json, recommendation, outcome_status) VALUES (2, 1, 1, 1, 1, 'Duplicate', 'Question', 'general', 'open', '{}', 'Review facts', 'not_recorded')"))
    downgrade(database, "20260809_0019")
    assert "personal_decisions" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT goal FROM intelligence_sessions WHERE id = 1")).scalar_one() == "Question"
    upgrade(database, "20260811_0021")
    assert "20260811_0021" in current(database)
