from sqlalchemy import create_engine, inspect

from tests.migrations.helpers import downgrade, upgrade


def test_strategy_persistence_upgrade_and_downgrade_preserve_legacy_table(tmp_path):
    database = tmp_path / "strategy-persistence.db"
    upgrade(database, "20260921_0023")
    engine = create_engine(f"sqlite:///{database}")
    legacy_columns = {column["name"] for column in inspect(engine).get_columns("strategies")}

    upgrade(database, "20260923_0024")
    inspector = inspect(engine)
    assert {"strategy_resources", "strategy_revisions", "strategies"} <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("strategies")} == legacy_columns
    assert {
        "id", "public_id", "title", "created_by_user_id", "owner_user_id",
        "organization_id", "workspace_id", "current_revision_number", "lock_version",
        "archived_at", "created_at", "updated_at",
    } == {column["name"] for column in inspector.get_columns("strategy_resources")}
    assert {
        "id", "strategy_id", "revision_number", "canonical_result_json",
        "snapshot_schema_version", "created_by_user_id", "origin_type",
        "source_decision_id", "created_at",
    } == {column["name"] for column in inspector.get_columns("strategy_revisions")}

    resource_checks = {item["name"] for item in inspector.get_check_constraints("strategy_resources")}
    revision_checks = {item["name"] for item in inspector.get_check_constraints("strategy_revisions")}
    assert {
        "ck_strategy_resources_title_nonempty", "ck_strategy_resources_current_revision_positive",
        "ck_strategy_resources_lock_version_positive", "ck_strategy_resources_tenancy_shape",
    } <= resource_checks
    assert {
        "ck_strategy_revisions_revision_positive", "ck_strategy_revisions_snapshot_schema_version_positive",
        "ck_strategy_revisions_origin_type", "ck_strategy_revisions_direct_source_decision",
    } <= revision_checks
    assert "uq_strategy_resources_public_id" in {
        item["name"] for item in inspector.get_unique_constraints("strategy_resources")
    }
    assert "uq_strategy_revisions_strategy_revision" in {
        item["name"] for item in inspector.get_unique_constraints("strategy_revisions")
    }
    assert {item["name"] for item in inspector.get_indexes("strategy_resources")} >= {
        "ix_strategy_resources_owner_archive_updated", "ix_strategy_resources_workspace_archive_updated",
        "ix_strategy_resources_created_by",
    }
    assert {item["name"] for item in inspector.get_indexes("strategy_revisions")} >= {
        "ix_strategy_revisions_strategy_created", "ix_strategy_revisions_source_decision",
    }

    downgrade(database, "20260921_0023")
    inspector = inspect(engine)
    assert "strategy_resources" not in inspector.get_table_names()
    assert "strategy_revisions" not in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("strategies")} == legacy_columns
