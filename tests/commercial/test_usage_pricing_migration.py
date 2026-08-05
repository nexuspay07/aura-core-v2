from sqlalchemy import create_engine, inspect, text

from tests.migrations.helpers import downgrade, upgrade


def test_usage_pricing_and_allocation_upgrade_downgrade_preserves_prior_schema(tmp_path):
    database = tmp_path / "usage-pricing.db"
    upgrade(database, "20260730_0014")
    engine = create_engine(f"sqlite:///{database}")
    assert "usage_records" in inspect(engine).get_table_names()
    upgrade(database)
    inspector = inspect(engine)
    assert {"usage_prices", "invoice_usage_allocations"} <= set(inspector.get_table_names())
    assert {"organization_id", "plan_id", "feature_key", "unit_price", "effective_from", "effective_until"} <= {c["name"] for c in inspector.get_columns("usage_prices")}
    assert {"usage_record_id", "invoice_id", "invoice_line_item_id", "quantity_allocated", "unit_price", "amount"} <= {c["name"] for c in inspector.get_columns("invoice_usage_allocations")}
    assert any(x["name"] == "uq_invoice_usage_allocations_usage_record" for x in inspector.get_unique_constraints("invoice_usage_allocations"))
    downgrade(database, "20260730_0014")
    tables = set(inspect(engine).get_table_names())
    assert "usage_prices" not in tables and "invoice_usage_allocations" not in tables and "usage_records" in tables
    upgrade(database)
    assert {"usage_prices", "invoice_usage_allocations"} <= set(inspect(engine).get_table_names())
