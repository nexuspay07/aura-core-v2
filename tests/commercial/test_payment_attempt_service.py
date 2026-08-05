from datetime import datetime,timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import *
from app.commercial.payment_attempt_service import *
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
@pytest.fixture
def s():
 e=create_engine('sqlite:///:memory:');event.listen(e,'connect',lambda d,_:d.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);x=sessionmaker(bind=e)();x.execute(insert(user_table).values(id=1,email='s@p',password_hash='x'));x.execute(insert(organization_table).values(id=1,name='o',slug='pas',owner_user_id=1,plan='free',subscription_status='inactive',is_active=True));x.add(Plan(id=1,code='p',name='p',seat_limit=1));x.flush();x.add_all([BillingAccount(id=1,organization_id=1,billing_email='a@p',billing_name='a',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=NOW)]);x.flush();x.add(Invoice(id=1,organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='I',status='open',currency='CAD',period_start=NOW,period_end=datetime(2026,2,1,tzinfo=timezone.utc),total_amount=Decimal('10'),amount_due=Decimal('10')));x.commit();yield x
def make(s,n=1,k='k'):
 return PaymentAttemptService(s,clock=lambda:NOW).create_attempt(invoice_id=1,attempt_number=n,provider='test',idempotency_key=k,amount=Decimal('1'),currency='CAD')
def test_create_and_lifecycle(s):
 x=make(s);assert x.status=='pending' and x.requested_at==NOW and x.version==1 and s.in_transaction();PaymentAttemptService(s,clock=lambda:NOW).start_processing(x.id);assert x.status=='processing';PaymentAttemptService(s,clock=lambda:NOW).mark_succeeded(x.id,'ref');assert x.status=='succeeded' and x.provider_reference=='ref';s.commit()
def test_failure_cancel_and_rollback(s):
 x=make(s);PaymentAttemptService(s).cancel_attempt(x.id);assert x.status=='cancelled';s.rollback();assert s.get(PaymentAttempt,x.id) is None
def test_invalid_transition(s):
 x=make(s)
 with pytest.raises(PaymentAttemptTransitionError):PaymentAttemptService(s).mark_failed(x.id)
