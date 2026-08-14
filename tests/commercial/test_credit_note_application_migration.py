from sqlalchemy import create_engine,inspect
from alembic.config import Config
from alembic.script import ScriptDirectory
from tests.migrations.helpers import upgrade,downgrade
def test_credit_application_migration(tmp_path):
 d=tmp_path/'app.db';upgrade(d);i=inspect(create_engine(f'sqlite:///{d}'));assert 'credit_note_applications' in i.get_table_names();cols={x['name'] for x in i.get_columns('credit_note_applications')};assert {'organization_id','credit_note_id','invoice_id','idempotency_key','amount'}<=cols
 assert ScriptDirectory.from_config(Config('alembic.ini')).get_heads()==['20260811_0021'];downgrade(d,'20260728_0011');assert 'credit_note_applications' not in inspect(create_engine(f'sqlite:///{d}')).get_table_names();upgrade(d,'20260728_0012')
