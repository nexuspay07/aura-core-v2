from sqlalchemy import create_engine, inspect

from tests.migrations.helpers import downgrade, upgrade


def test_simulation_persistence_upgrade_and_downgrade_preserve_legacy_history(tmp_path):
    database = tmp_path / "simulation-persistence.db"
    upgrade(database, "20260924_0026")
    engine = create_engine(f"sqlite:///{database}")
    legacy_columns = {column["name"] for column in inspect(engine).get_columns("simulation_history")}

    upgrade(database, "20261006_0027")
    inspector = inspect(engine)
    assert {"simulation_resources", "simulation_runs", "simulation_history"} <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("simulation_history")} == legacy_columns
    assert {
        "id", "public_id", "title", "simulation_type", "created_by_user_id",
        "owner_user_id", "organization_id", "workspace_id", "source_strategy_id",
        "source_strategy_revision_id", "source_decision_snapshot_id",
        "current_run_number", "lock_version", "archived_at", "created_at", "updated_at",
    } == {column["name"] for column in inspector.get_columns("simulation_resources")}
    assert {
        "id", "simulation_resource_id", "run_number", "canonical_execution_input_json",
        "canonical_result_json", "input_schema_version", "result_schema_version",
        "engine_version", "provider_name", "model_name", "determinism_mode",
        "created_by_user_id", "created_at",
    } == {column["name"] for column in inspector.get_columns("simulation_runs")}
    assert "uq_simulation_resources_public_id" in {
        item["name"] for item in inspector.get_unique_constraints("simulation_resources")
    }
    assert "uq_simulation_runs_resource_run" in {
        item["name"] for item in inspector.get_unique_constraints("simulation_runs")
    }
    assert {item["name"] for item in inspector.get_indexes("simulation_resources")} >= {
        "ix_simulation_resources_owner_archive_updated",
        "ix_simulation_resources_workspace_archive_updated",
        "ix_simulation_resources_strategy_revision",
    }

    downgrade(database, "20260924_0026")
    inspector = inspect(engine)
    assert "simulation_resources" not in inspector.get_table_names()
    assert "simulation_runs" not in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("simulation_history")} == legacy_columns
