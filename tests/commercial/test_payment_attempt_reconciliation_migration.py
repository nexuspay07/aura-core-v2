from sqlalchemy import create_engine,inspect
from tests.migrations.helpers import upgrade,downgrade
def test_reconciled_marker_migration(tmp_path):
 d=tmp_path/'r.db';upgrade(d,'20260728_0010');i=inspect(create_engine(f'sqlite:///{d}'));cols={c['name']:c for c in i.get_columns('payment_attempts')};assert 'reconciled_at' in cols and cols['reconciled_at']['nullable'];downgrade(d,'20260728_0009');assert 'reconciled_at' not in {c['name'] for c in inspect(create_engine(f'sqlite:///{d}')).get_columns('payment_attempts')};upgrade(d,'20260728_0010')
