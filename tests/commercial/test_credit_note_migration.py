from datetime import datetime, timezone
from decimal import Decimal

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.migrations.helpers import downgrade, upgrade


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def connection(database):
    engine = create_engine(f"sqlite:///{database}")
    return engine, engine.connect()


def seed_pre_credit_schema(database):
    upgrade(database, "20260728_0010")
    engine, conn = connection(database)
    try:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("""INSERT INTO invoices (id,organization_id,billing_account_id,subscription_id,invoice_number,status,currency,period_start,period_end,subtotal_amount,tax_amount,discount_amount,total_amount,amount_due,amount_paid,version,created_at,updated_at) VALUES (1,1,1,1,'INV-PRESERVED','open','CAD',:now,:end,10,0,0,10,10,0,1,:now,:now)"""), {"now": NOW, "end": datetime(2026, 8, 1, tzinfo=timezone.utc)})
        conn.execute(text("""INSERT INTO payment_attempts (id,invoice_id,attempt_number,provider,idempotency_key,status,amount,currency,requested_at,reconciled_at,version,created_at,updated_at) VALUES (1,1,1,'fake','preserved-key','succeeded',10,'CAD',:now,:now,1,:now,:now)"""), {"now": NOW})
        conn.commit()
    finally:
        conn.close(); engine.dispose()


def test_revision_chain_and_upgrade_schema(tmp_path):
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = script.get_revision("20260728_0011")
    assert revision.revision == "20260728_0011" and revision.down_revision == "20260728_0010"
    database = tmp_path / "credit-notes.db"; upgrade(database)
    engine, conn = connection(database)
    try:
        inspector = inspect(conn)
        columns = {column["name"]: column for column in inspector.get_columns("credit_notes")}
        assert set(("id", "organization_id", "invoice_id", "credit_note_number", "status", "currency", "reason", "subtotal", "tax", "total", "amount_applied", "amount_remaining", "issued_at", "voided_at", "created_at", "updated_at", "version")) <= columns.keys()
        assert all(not columns[name]["nullable"] for name in ("organization_id", "invoice_id", "credit_note_number", "status", "currency"))
        assert {"ix_credit_notes_organization_id", "ix_credit_notes_invoice_id", "ix_credit_notes_status"} <= {index["name"] for index in inspector.get_indexes("credit_notes")}
        assert {"uq_credit_notes_organization_number", "ck_credit_notes_subtotal_nonnegative", "ck_credit_notes_balance_not_over_total"} <= {constraint["name"] for constraint in inspector.get_unique_constraints("credit_notes")} | {constraint["name"] for constraint in inspector.get_check_constraints("credit_notes")}
        assert {foreign_key["referred_table"] for foreign_key in inspector.get_foreign_keys("credit_notes")} == {"organizations", "invoices"}
        assert "credit_note_line_items" in inspector.get_table_names()
    finally:
        conn.close(); engine.dispose()
    assert script.get_heads() == ["20260815_0022"]


def test_upgrade_preserves_existing_commercial_records_and_accepts_valid_credit_note(tmp_path):
    database = tmp_path / "preserve.db"; seed_pre_credit_schema(database); upgrade(database, "20260728_0011")
    engine, conn = connection(database)
    try:
        assert conn.execute(text("SELECT reconciled_at FROM payment_attempts WHERE id=1")).scalar_one() is not None
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        payload = {"now": NOW}
        conn.execute(text("""INSERT INTO credit_notes (id,organization_id,invoice_id,credit_note_number,status,currency,subtotal,tax,total,amount_applied,amount_remaining,created_at,updated_at,version) VALUES (1,1,1,'CN-1','draft','CAD',10,0,10,0,10,:now,:now,1)"""), payload)
        conn.execute(text("""INSERT INTO credit_note_line_items (id,credit_note_id,line_number,description,quantity,unit_amount,subtotal,tax,total,created_at) VALUES (1,1,1,'credit',1,10,10,0,10,:now)"""), payload)
        conn.commit()
        assert conn.execute(text("SELECT total FROM credit_notes WHERE id=1")).scalar_one() == 10
    finally:
        conn.close(); engine.dispose()


def test_unique_and_money_constraints_are_enforced(tmp_path):
    database = tmp_path / "constraints.db"; seed_pre_credit_schema(database); upgrade(database)
    engine, conn = connection(database)
    try:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        statement = text("""INSERT INTO credit_notes (id,organization_id,invoice_id,credit_note_number,status,currency,subtotal,tax,total,amount_applied,amount_remaining,created_at,updated_at,version) VALUES (:id,:organization_id,1,:number,'draft','CAD',:subtotal,0,10,0,10,:now,:now,1)""")
        conn.execute(statement, {"id": 1, "organization_id": 1, "number": "CN-1", "subtotal": 10, "now": NOW}); conn.commit()
        with pytest.raises(IntegrityError):
            conn.execute(statement, {"id": 2, "organization_id": 1, "number": "CN-1", "subtotal": 10, "now": NOW})
        conn.rollback()
        conn.execute(statement, {"id": 2, "organization_id": 2, "number": "CN-1", "subtotal": 10, "now": NOW}); conn.commit()
        with pytest.raises(IntegrityError):
            conn.execute(statement, {"id": 3, "organization_id": 1, "number": "CN-negative", "subtotal": -1, "now": NOW})
    finally:
        conn.close(); engine.dispose()


def test_downgrade_removes_only_credit_note_tables_and_reupgrade_succeeds(tmp_path):
    database = tmp_path / "downgrade.db"; seed_pre_credit_schema(database); upgrade(database)
    downgrade(database, "20260728_0010")
    engine, conn = connection(database)
    try:
        tables = set(inspect(conn).get_table_names())
        assert "credit_notes" not in tables and "credit_note_line_items" not in tables
        assert {"invoices", "payment_attempts", "billing_accounts", "plans"} <= tables
        assert conn.execute(text("SELECT invoice_number FROM invoices WHERE id=1")).scalar_one() == "INV-PRESERVED"
    finally:
        conn.close(); engine.dispose()
    upgrade(database, "20260728_0011")
    engine, conn = connection(database)
    try:
        assert "credit_notes" in inspect(conn).get_table_names()
        assert conn.execute(text("SELECT id FROM payment_attempts WHERE id=1")).scalar_one() == 1
    finally:
        conn.close(); engine.dispose()
