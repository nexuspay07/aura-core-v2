from datetime import datetime,timezone
from app.commercial.models import PaymentAttempt
def test_reconciled_marker_mapping():
 c=PaymentAttempt.__table__.c.reconciled_at;assert c.nullable and PaymentAttempt().reconciled_at is None
def test_reconciled_timestamp_assignment():
 a=PaymentAttempt();t=datetime(2026,1,1,tzinfo=timezone.utc);a.reconciled_at=t;assert a.reconciled_at==t
