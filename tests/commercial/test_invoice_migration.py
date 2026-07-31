from sqlalchemy import create_engine,inspect
from tests.migrations.helpers import upgrade,downgrade

def test_invoice_migration_chain(tmp_path):
 db=tmp_path/"invoices.db";upgrade(db,"20260728_0008")
 i=inspect(create_engine(f"sqlite:///{db}"));assert {"invoices","invoice_line_items"}<=set(i.get_table_names())
 assert {"id","organization_id","billing_account_id","subscription_id","invoice_number","status","currency","subtotal_amount","amount_paid","version"}<={c["name"] for c in i.get_columns("invoices")}
 assert {"id","invoice_id","line_number","item_type","quantity","unit_amount","total_amount"}<={c["name"] for c in i.get_columns("invoice_line_items")}
 assert {f["referred_table"] for f in i.get_foreign_keys("invoices")}=={"organizations","billing_accounts","subscriptions"}
 assert {f["referred_table"] for f in i.get_foreign_keys("invoice_line_items")}=={"invoices"}
 downgrade(db,"20260728_0007");i=inspect(create_engine(f"sqlite:///{db}"));assert "invoices" not in i.get_table_names() and "plans" in i.get_table_names()
 upgrade(db,"20260728_0008");assert "invoices" in inspect(create_engine(f"sqlite:///{db}")).get_table_names()
