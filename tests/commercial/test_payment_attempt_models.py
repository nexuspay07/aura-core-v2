from datetime import datetime,timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine,event
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table  # noqa: F401
from app.commercial.models import PaymentAttempt
def test_payment_attempt_model_constraints_and_columns():
 assert {"invoice_id","attempt_number","provider","idempotency_key","status","amount","currency","requested_at"}<={c.name for c in PaymentAttempt.__table__.columns}
 assert "Float" not in str(PaymentAttempt.__table__.c.amount.type)
def test_payment_attempt_requires_invoice_sqlite():
 e=create_engine("sqlite:///:memory:");event.listen(e,"connect",lambda d,_:d.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);s=sessionmaker(bind=e)();s.add(PaymentAttempt(invoice_id=99,attempt_number=1,provider="provider",idempotency_key="key",amount=Decimal("1"),currency="CAD",requested_at=datetime.now(timezone.utc)))
 with pytest.raises(Exception):s.commit()
