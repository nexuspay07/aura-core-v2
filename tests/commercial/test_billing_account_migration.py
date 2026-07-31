from sqlalchemy import create_engine, inspect, text
from tests.migrations.helpers import upgrade, downgrade

def test_billing_account_migration_upgrade_downgrade_and_reupgrade(tmp_path):
 database=tmp_path/"billing.db"; upgrade(database,"20260728_0006")
 engine=create_engine(f"sqlite:///{database}")
 with engine.begin() as c:
  c.execute(text("INSERT INTO users (id,email,password_hash) VALUES (1,'migration-billing@test','x')"))
  c.execute(text("INSERT INTO organizations (id,name,slug,owner_user_id,plan,subscription_status,is_active) VALUES (1,'Aura','billing-migration',1,'free','inactive',1)"))
 upgrade(database,"20260728_0007");i=inspect(engine);assert "billing_accounts" in i.get_table_names()
 cols={x["name"]:x for x in i.get_columns("billing_accounts")};assert {"id","organization_id","billing_email","billing_name","country_code","currency","billing_status","version","created_at","updated_at"}<=set(cols);assert not cols["organization_id"]["nullable"]
 assert {f["referred_table"] for f in i.get_foreign_keys("billing_accounts")}=={"organizations"}
 assert any(x["name"]=="uq_billing_accounts_organization" for x in i.get_unique_constraints("billing_accounts"))
 assert {x["name"] for x in i.get_indexes("billing_accounts")} >= {"ix_billing_accounts_organization_id","ix_billing_accounts_billing_status"}
 with engine.begin() as c:c.execute(text("INSERT INTO billing_accounts (organization_id,billing_email,billing_name,country_code,currency,billing_status,version,created_at,updated_at) VALUES (1,'a@test','A','CA','CAD','active',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
 downgrade(database,"20260728_0006");assert "billing_accounts" not in inspect(engine).get_table_names();assert "organizations" in inspect(engine).get_table_names()
 upgrade(database,"20260728_0007");assert "billing_accounts" in inspect(engine).get_table_names()
