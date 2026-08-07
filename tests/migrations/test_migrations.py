from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text

from app.db.schema import target_metadata
from tests.migrations.helpers import current, downgrade, upgrade

def _expected_tables():
    return {table.name for metadata in target_metadata for table in metadata.tables.values()}

def test_fresh_database_upgrades_to_head(tmp_path):
    database = tmp_path / "fresh.db"
    upgrade(database)
    inspector = inspect(create_engine(f"sqlite:///{database}"))
    assert _expected_tables() <= set(inspector.get_table_names())
    assert "20260807_0017" in current(database)

def test_schema_columns_and_indexes_match_metadata(tmp_path):
    database = tmp_path / "schema.db"
    upgrade(database)
    inspector = inspect(create_engine(f"sqlite:///{database}"))
    for metadata in target_metadata:
        for table in metadata.tables.values():
            actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
            expected_columns = {column.name for column in table.columns}
            assert expected_columns <= actual_columns, f"{table.name}: missing columns {expected_columns - actual_columns}"
            actual_indexes = {index["name"] for index in inspector.get_indexes(table.name)}
            expected_indexes = {index.name for index in table.indexes if index.name}
            assert expected_indexes <= actual_indexes, f"{table.name}: missing indexes {expected_indexes - actual_indexes}"

def test_revision_chain_has_one_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["20260807_0017"]
    assert script.get_revision("20260728_0001").down_revision is None
    assert script.get_revision("20260807_0017").down_revision == "20260731_0016"


def test_subscription_history_migration_constraints_indexes_and_upgrade_downgrade(tmp_path):
    database = tmp_path / "subscriptions.db"
    upgrade(database, "20260728_0003")
    engine = create_engine(f"sqlite:///{database}")
    timestamp = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, email, password_hash) VALUES (1, 'migration@example.test', 'test')"))
        connection.execute(text("INSERT INTO organizations (id, name, slug, owner_user_id, plan, subscription_status, is_active) VALUES (1, 'Aura', 'aura-migration', 1, 'free', 'inactive', 1)"))
        connection.execute(text("INSERT INTO plans (id, code, name, seat_limit, is_active, version, created_at, updated_at) VALUES (1, 'migration', 'Migration', 1, 1, 1, :timestamp, :timestamp)"), {"timestamp": timestamp})
        connection.execute(text("INSERT INTO plan_features (id, plan_id, feature_key, value_type, is_enabled, version, created_at, updated_at) VALUES (1, 1, 'feature', 'boolean', 1, 1, :timestamp, :timestamp)"), {"timestamp": timestamp})

    upgrade(database, "20260728_0004")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO subscriptions (id, organization_id, plan_id, status, billing_cycle, starts_at, version, created_at, updated_at) VALUES (1, 1, 1, 'active', 'monthly', :timestamp, 1, :timestamp, :timestamp)"), {"timestamp": timestamp})

    upgrade(database, "20260728_0005")
    upgrade(database, "20260728_0006")
    inspector = inspect(engine)
    assert "usage_records" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("usage_records")} >= {"organization_id", "subscription_id", "feature_key", "quantity", "unit", "occurred_at", "idempotency_key"}
    assert {index["name"] for index in inspector.get_indexes("usage_records")} >= {"ix_usage_records_organization_id", "ix_usage_records_subscription_id", "ix_usage_records_feature_key", "ix_usage_records_occurred_at", "ix_usage_records_organization_feature_occurred", "ix_usage_records_idempotency_key"}
    assert {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("usage_records")} == {"organizations", "subscriptions"}
    assert {"ck_usage_records_quantity_positive", "ck_usage_records_source_type"} <= {check["name"] for check in inspector.get_check_constraints("usage_records")}
    assert any(item["name"] == "uq_usage_records_organization_idempotency" for item in inspector.get_unique_constraints("usage_records"))
    assert "subscription_history" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("subscription_history")} >= {
        "id", "subscription_id", "event_type", "previous_status", "new_status", "previous_plan_id",
        "new_plan_id", "effective_at", "metadata_json", "created_at",
    }
    assert {index["name"] for index in inspector.get_indexes("subscription_history")} >= {
        "ix_subscription_history_subscription_id", "ix_subscription_history_event_type",
        "ix_subscription_history_effective_at", "ix_subscription_history_subscription_effective",
        "ix_subscription_history_external_reference",
    }
    assert {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("subscription_history")} == {"subscriptions", "plans"}
    checks = {check["name"] for check in inspector.get_check_constraints("subscription_history")}
    assert {"ck_subscription_history_event_type", "ck_subscription_history_previous_status", "ck_subscription_history_new_status", "ck_subscription_history_change_values"} <= checks
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM organizations WHERE id = 1")).scalar_one() == "Aura"
        assert connection.execute(text("SELECT code FROM plans WHERE id = 1")).scalar_one() == "migration"
        assert connection.execute(text("SELECT feature_key FROM plan_features WHERE id = 1")).scalar_one() == "feature"
        assert connection.execute(text("SELECT status FROM subscriptions WHERE id = 1")).scalar_one() == "active"

    downgrade(database, "20260728_0005")
    assert "usage_records" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT status FROM subscriptions WHERE id = 1")).scalar_one() == "active"
