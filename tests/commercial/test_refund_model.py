from sqlalchemy import create_engine,event,inspect
from app.db import user_table,organization_table
from app.db.database import Base
from app.commercial.models import Refund
def test_refund_model_schema():
 e=create_engine('sqlite:///:memory:');event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);c={x['name']:x for x in inspect(e).get_columns('refunds')};assert {'organization_id','invoice_id','payment_attempt_id','credit_note_id','refund_number','amount','idempotency_key','provider','reconciled_at'}<=c.keys();assert c['credit_note_id']['nullable'];assert Refund.__table__.c.amount.type.scale==4
