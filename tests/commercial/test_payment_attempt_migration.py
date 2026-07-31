from sqlalchemy import create_engine,inspect
from tests.migrations.helpers import upgrade,downgrade
def test_payment_attempt_migration(tmp_path):
 d=tmp_path/"p.db";upgrade(d,"20260728_0009");i=inspect(create_engine(f"sqlite:///{d}"));assert "payment_attempts" in i.get_table_names();assert {"id","invoice_id","amount","idempotency_key","requested_at"}<={c["name"] for c in i.get_columns("payment_attempts")};assert {"ix_payment_attempts_invoice_id","ix_payment_attempts_status","ix_payment_attempts_provider","ix_payment_attempts_requested_at"}<={x["name"] for x in i.get_indexes("payment_attempts")};downgrade(d,"20260728_0008");assert "payment_attempts" not in inspect(create_engine(f"sqlite:///{d}")).get_table_names()
