from sqlalchemy import create_engine, inspect

from tests.migrations.helpers import downgrade, upgrade


def test_simulation_idempotency_upgrade_and_downgrade_leave_strategy_table_unchanged(tmp_path):
    database = tmp_path / "simulation-idempotency.db"
    upgrade(database, "20261006_0027")
    engine = create_engine(f"sqlite:///{database}")
    strategy_columns = {item["name"] for item in inspect(engine).get_columns("strategy_create_idempotency")}

    upgrade(database, "20261006_0028")
    inspector = inspect(engine)
    assert "simulation_create_idempotency" in inspector.get_table_names()
    assert {item["name"] for item in inspector.get_columns("strategy_create_idempotency")} == strategy_columns
    assert {
        "id", "idempotency_key", "operation", "request_fingerprint", "actor_user_id",
        "owner_user_id", "organization_id", "workspace_id", "status", "claim_token",
        "lease_expires_at", "simulation_resource_id", "created_at", "updated_at",
    } == {item["name"] for item in inspector.get_columns("simulation_create_idempotency")}
    foreign_keys = {item["referred_table"] for item in inspector.get_foreign_keys("simulation_create_idempotency")}
    assert "simulation_resources" in foreign_keys
    assert "strategy_resources" not in foreign_keys
    assert {item["name"] for item in inspector.get_indexes("simulation_create_idempotency")} >= {
        "uq_simulation_create_idempotency_personal_key",
        "uq_simulation_create_idempotency_workspace_key",
        "ix_simulation_create_idempotency_resource",
        "ix_simulation_create_idempotency_status_lease",
    }

    downgrade(database, "20261006_0027")
    inspector = inspect(engine)
    assert "simulation_create_idempotency" not in inspector.get_table_names()
    assert {item["name"] for item in inspector.get_columns("strategy_create_idempotency")} == strategy_columns
