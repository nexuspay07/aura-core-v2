from sqlalchemy import create_engine,inspect
from alembic.config import Config
from alembic.script import ScriptDirectory
from tests.migrations.helpers import upgrade,downgrade
def test_refund_migration(tmp_path):
 d=tmp_path/'r.db';upgrade(d);i=inspect(create_engine(f'sqlite:///{d}'));assert 'refunds' in i.get_table_names();assert {'organization_id','invoice_id','payment_attempt_id','amount'}<={x['name'] for x in i.get_columns('refunds')};assert ScriptDirectory.from_config(Config('alembic.ini')).get_heads()==['20260731_0016'];downgrade(d,'20260728_0012');assert 'refunds' not in inspect(create_engine(f'sqlite:///{d}')).get_table_names();upgrade(d,'20260728_0013')
