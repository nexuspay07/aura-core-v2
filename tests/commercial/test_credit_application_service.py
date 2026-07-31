from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import Plan, BillingAccount, Subscription, Invoice, CreditNote, CreditNoteApplication
from app.commercial.credit_application_service import CreditApplicationService
from app.commercial.billing import BillingError, BillingPersistenceConflictError

N = datetime(2026, 7, 29, 16, tzinfo=timezone.utc)

@pytest.fixture
def s():
    e=create_engine('sqlite:///:memory:'); event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON')); Base.metadata.create_all(e); x=sessionmaker(bind=e,expire_on_commit=False)()
    x.execute(insert(user_table).values(id=1,email='ca@test',password_hash='x')); x.execute(insert(organization_table).values(id=1,name='o',slug='ca',owner_user_id=1,plan='free',subscription_status='inactive',is_active=True))
    x.add_all([Plan(id=1,code='ca',name='ca',seat_limit=1),BillingAccount(id=1,organization_id=1,billing_email='a@b',billing_name='a',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=N)]); x.flush()
    x.add(Invoice(id=1,organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='I-CA',status='open',currency='CAD',period_start=N,period_end=N+timedelta(days=31),subtotal_amount=Decimal('10'),tax_amount=0,discount_amount=0,total_amount=Decimal('10'),amount_due=Decimal('10'),amount_paid=0)); x.flush()
    x.add(CreditNote(id=1,organization_id=1,invoice_id=1,credit_note_number='CN-CA',status='issued',currency='CAD',subtotal=Decimal('10'),tax=0,total=Decimal('10'),amount_applied=0,amount_remaining=Decimal('10'),issued_at=N,created_at=N,updated_at=N)); x.commit()
    yield x

def svc(s): return CreditApplicationService(s,clock=lambda:N)

def test_partial_full_replay_and_transactions(s):
    r=svc(s).apply_credit(1,amount=Decimal('4.0000'),idempotency_key='k1'); assert r.application.amount==Decimal('4.0000') and r.credit_note.amount_remaining==Decimal('6.0000') and r.invoice.amount_due==Decimal('6.0000') and r.credit_note.status=='issued'
    versions=(r.credit_note.version,r.invoice.version); again=svc(s).apply_credit(1,amount=Decimal('4'),idempotency_key='k1'); assert again.application.id==r.application.id and (again.credit_note.version,again.invoice.version)==versions
    final=svc(s).apply_credit(1,amount=Decimal('6'),idempotency_key='k2'); assert final.credit_note.status=='fully_applied' and final.invoice.amount_due==0 and final.invoice.paid_at is None
    s.rollback(); s.expire_all(); assert s.get(CreditNoteApplication,1) is None and s.get(CreditNote,1).amount_remaining==Decimal('10.0000')

def test_validation_conflicts_and_no_float(s):
    with pytest.raises(BillingError): svc(s).apply_credit(0,amount=1,idempotency_key='x')
    with pytest.raises(BillingError): svc(s).apply_credit(1,amount=0,idempotency_key='x')
    with pytest.raises(BillingError): svc(s).apply_credit(1,amount=1.0,idempotency_key='x')
    with pytest.raises(BillingError): svc(s).apply_credit(1,amount=11,idempotency_key='x')
    svc(s).apply_credit(1,amount=1,idempotency_key='same')
    with pytest.raises(BillingPersistenceConflictError): svc(s).apply_credit(1,amount=2,idempotency_key='same')
