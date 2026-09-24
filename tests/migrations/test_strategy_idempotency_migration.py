from sqlalchemy import create_engine, inspect

from tests.migrations.helpers import downgrade, upgrade


def test_strategy_idempotency_upgrade_constraints_indexes_and_downgrade(tmp_path):
    database = tmp_path / "strategy-idempotency.db"
    upgrade(database, "20260923_0024")
    engine = create_engine(f"sqlite:///{database}")
    before = set(inspect(engine).get_table_names())
    upgrade(database, "20260924_0025")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == before | {"strategy_create_idempotency"}
    assert {column["name"] for column in inspector.get_columns("strategy_create_idempotency")} == {
        "id", "idempotency_key", "operation", "request_fingerprint", "actor_user_id",
        "owner_user_id", "organization_id", "workspace_id", "status", "claim_token",
        "lease_expires_at", "strategy_resource_id", "created_at", "updated_at",
    }
    assert {item["name"] for item in inspector.get_check_constraints("strategy_create_idempotency")} >= {
        "ck_strategy_create_idempotency_key_nonempty", "ck_strategy_create_idempotency_fingerprint",
        "ck_strategy_create_idempotency_operation", "ck_strategy_create_idempotency_status",
        "ck_strategy_create_idempotency_tenancy_shape", "ck_strategy_create_idempotency_state",
    }
    assert {item["name"] for item in inspector.get_indexes("strategy_create_idempotency")} >= {
        "uq_strategy_create_idempotency_personal_key", "uq_strategy_create_idempotency_workspace_key",
        "ix_strategy_create_idempotency_resource", "ix_strategy_create_idempotency_status_lease",
    }
    assert {item["referred_table"] for item in inspector.get_foreign_keys("strategy_create_idempotency")} == {
        "users", "organizations", "workspaces", "strategy_resources",
    }
    downgrade(database, "20260923_0024")
    assert "strategy_create_idempotency" not in inspect(engine).get_table_names()
