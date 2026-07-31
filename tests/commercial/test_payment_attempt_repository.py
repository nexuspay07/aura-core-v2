from datetime import datetime,timezone,timedelta
from decimal import Decimal
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import *
from app.commercial.repositories import SqlAlchemyPaymentAttemptRepository
from app.commercial.billing import BillingPersistenceConflictError
@pytest.fixture
def s():
 e=create_engine('sqlite:///:memory:');event.listen(e,'connect',lambda d,_:d.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);x=sessionmaker(bind=e)();x.execute(insert(user_table).values(id=1,email='p@r',password_hash='x'));x.execute(insert(organization_table).values(id=1,name='o',slug='par',owner_user_id=1,plan='free',subscription_status='inactive',is_active=True));x.add(Plan(id=1,code='p',name='p',seat_limit=1));x.flush();x.add_all([BillingAccount(id=1,organization_id=1,billing_email='a@r',billing_name='a',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=datetime.now(timezone.utc))]);x.flush();x.add(Invoice(id=1,organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='I',status='draft',currency='CAD',period_start=datetime(2026,1,1,tzinfo=timezone.utc),period_end=datetime(2026,2,1,tzinfo=timezone.utc)));x.commit();yield x
def a(n=1,k='k',when=None):return PaymentAttempt(invoice_id=1,attempt_number=n,provider='test',provider_reference='r',idempotency_key=k,amount=Decimal('1'),currency='CAD',requested_at=when or datetime(2026,1,1,tzinfo=timezone.utc))
def test_save_queries_relationships_and_no_commit(s):
 r=SqlAlchemyPaymentAttemptRepository(s);x=r.save(a());assert x.id and s.in_transaction();s.commit();assert r.get_by_id(x.id).invoice.id==1 and r.get_by_idempotency_key('k').id==x.id and r.get_by_provider_reference('test','r').id==x.id and r.list_by_invoice_id(1)==[x] and r.list_by_status('pending')==[x] and r.list_by_provider('test')==[x] and r.list_requested_before(datetime(2026,1,1,tzinfo=timezone.utc))==[] and not hasattr(r,'commit') and not hasattr(r,'delete')
def test_missing_rollback_and_conflicts(s):
 r=SqlAlchemyPaymentAttemptRepository(s);assert r.get_by_id(9) is None and r.get_by_idempotency_key('x') is None and r.get_by_provider_reference('x','r') is None and r.list_by_invoice_id(9)==[];x=r.save(a());i=x.id;s.rollback();assert r.get_by_id(i) is None;x=r.save(a());s.commit()
 with pytest.raises(BillingPersistenceConflictError):r.save(a(2,'k'))
 s.rollback();assert not hasattr(r,'rollback')
