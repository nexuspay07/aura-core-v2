from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker
from app.commercial.models import BillingAccount, Invoice, Payment, Plan, Subscription
from app.commercial.payment_processing import PaymentProcessingService
from app.commercial.payment_providers import FakePaymentProvider, PaymentProviderRegistry
from app.commercial.payment_attempt_service import PaymentAttemptError, PaymentAttemptTransitionError
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
@pytest.fixture
def s():
 e=create_engine('sqlite:///:memory:');event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);x=sessionmaker(bind=e)();x.execute(insert(user_table),[{'id':1,'email':'pay@test','password_hash':'x'},{'id':2,'email':'other@test','password_hash':'x'}]);x.execute(insert(organization_table),[{'id':1,'name':'one','slug':'pay-one','owner_user_id':1,'plan':'free','subscription_status':'inactive','is_active':True},{'id':2,'name':'two','slug':'pay-two','owner_user_id':2,'plan':'free','subscription_status':'inactive','is_active':True}]);x.add(Plan(id=1,code='pay',name='Pay',seat_limit=1));x.add_all([BillingAccount(id=1,organization_id=1,billing_email='a@a',billing_name='a',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=NOW)]);x.flush();x.add(Invoice(id=1,organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='PAY-1',status='open',currency='CAD',period_start=NOW,period_end=datetime(2026,2,1,tzinfo=timezone.utc),total_amount=Decimal('10'),amount_due=Decimal('10')));x.commit();yield x
def service(s,outcome='succeeded'):
 r=PaymentProviderRegistry();r.register(FakePaymentProvider(outcome));return PaymentProcessingService(s,r,clock=lambda:NOW)
def test_full_payment_creates_one_payment_updates_invoice_and_is_idempotent(s):
 x=service(s);attempt=x.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='p1',amount=Decimal('10'),currency='CAD');assert x.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='p1',amount=Decimal('10'),currency='CAD') is attempt;x.execute(organization_id=1,attempt_id=attempt.id);invoice=s.get(Invoice,1);assert invoice.status=='paid' and invoice.amount_due==0 and s.query(Payment).count()==1;x.reconcile(organization_id=1,attempt_id=attempt.id);assert s.query(Payment).count()==1
def test_partial_and_failed_payments_preserve_correct_balance(s):
 x=service(s);a=x.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='partial',amount=Decimal('4'),currency='CAD');x.execute(organization_id=1,attempt_id=a.id);assert s.get(Invoice,1).amount_due==Decimal('6.0000') and s.query(Payment).count()==1;failed=service(s,'failed');a=failed.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='fail',amount=Decimal('1'),currency='CAD');failed.execute(organization_id=1,attempt_id=a.id);assert a.status=='failed' and s.query(Payment).count()==1 and s.get(Invoice,1).amount_due==Decimal('6.0000')
def test_invalid_status_currency_and_cross_organization_are_rejected(s):
 x=service(s);invoice=s.get(Invoice,1);invoice.status='draft'
 with pytest.raises(PaymentAttemptError):x.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='draft',amount=Decimal('1'),currency='CAD')
 invoice.status='open'
 with pytest.raises(PaymentAttemptError):x.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='usd',amount=Decimal('1'),currency='USD')
 with pytest.raises(PaymentAttemptError):x.create_attempt(organization_id=2,invoice_id=1,provider='fake',idempotency_key='other',amount=Decimal('1'),currency='CAD')
def test_terminal_and_unresolved_reconciliation_are_rejected(s):
 x=service(s,'processing');a=x.create_attempt(organization_id=1,invoice_id=1,provider='fake',idempotency_key='processing',amount=Decimal('1'),currency='CAD');x.execute(organization_id=1,attempt_id=a.id)
 with pytest.raises(PaymentAttemptTransitionError):x.reconcile(organization_id=1,attempt_id=a.id)
 s.rollback();assert s.query(Payment).count()==0
