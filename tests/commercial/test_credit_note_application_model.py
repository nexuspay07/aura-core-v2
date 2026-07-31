from datetime import datetime,timezone
from decimal import Decimal
from sqlalchemy import create_engine,event,inspect
from app.db.database import Base
from app.db import user_table, organization_table  # noqa: F401
from app.commercial.models import CreditNoteApplication
def test_application_model_metadata_and_defaults():
 e=create_engine('sqlite:///:memory:');event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e)
 cols={c['name']:c for c in inspect(e).get_columns('credit_note_applications')}
 assert {'id','organization_id','credit_note_id','invoice_id','idempotency_key','amount','currency','applied_at','created_at','version'}<=cols.keys()
 assert all(not cols[x]['nullable'] for x in cols)
 assert CreditNoteApplication.__table__.c.amount.type.precision==18 and CreditNoteApplication.__table__.c.amount.type.scale==4
 assert list(Base.metadata.tables).count('credit_note_applications')==1
