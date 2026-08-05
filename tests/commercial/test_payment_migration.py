from sqlalchemy import create_engine, inspect
from tests.migrations.helpers import downgrade, upgrade

def test_payment_migration_upgrade_downgrade(tmp_path):
 database=tmp_path/'payments.db';upgrade(database,'20260731_0015');engine=create_engine(f'sqlite:///{database}');assert 'payments' not in inspect(engine).get_table_names();upgrade(database)
 inspector=inspect(engine);assert 'payments' in inspector.get_table_names();assert {'organization_id','invoice_id','payment_attempt_id','provider','provider_reference','amount','currency','paid_at'}<={c['name'] for c in inspector.get_columns('payments')};assert {'uq_payments_attempt','uq_payments_provider_reference'}<={c['name'] for c in inspector.get_unique_constraints('payments')};downgrade(database,'20260731_0015');assert 'payments' not in inspect(engine).get_table_names();upgrade(database);assert 'payments' in inspect(engine).get_table_names()
