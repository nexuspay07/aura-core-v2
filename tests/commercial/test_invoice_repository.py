from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import *
from app.commercial.repositories import SqlAlchemyInvoiceRepository
from app.commercial.billing import BillingPersistenceConflictError
@pytest.fixture
def s():
 e=create_engine("sqlite:///:memory:");event.listen(e,"connect",lambda d,_:d.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);x=sessionmaker(bind=e)();x.execute(insert(user_table).values(id=1,email="r@i",password_hash="x"));x.execute(insert(organization_table).values(id=1,name="o",slug="ir",owner_user_id=1,plan="free",subscription_status="inactive",is_active=True));x.add(Plan(id=1,code="p",name="p",seat_limit=1));x.flush();x.add_all([BillingAccount(id=1,organization_id=1,billing_email="a@i",billing_name="a",country_code="CA",currency="CAD"),Subscription(id=1,organization_id=1,plan_id=1,status="active",billing_cycle="monthly",starts_at=datetime.now(timezone.utc))]);x.commit();yield x
def inv(n="I1",due=None):return Invoice(organization_id=1,billing_account_id=1,subscription_id=1,invoice_number=n,status="draft",currency="CAD",period_start=datetime(2026,1,1,tzinfo=timezone.utc),period_end=datetime(2026,2,1,tzinfo=timezone.utc),due_at=due)
def test_save_lookup_lists_relationships_and_no_commit(s):
 r=SqlAlchemyInvoiceRepository(s);a=r.save(inv(due=datetime(2026,2,1,tzinfo=timezone.utc)));assert s.in_transaction();s.flush();s.add(InvoiceLineItem(invoice_id=a.id,line_number=1,item_type="usage",description="x",quantity=1,unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1));s.commit();assert r.get_by_id(a.id).organization.id==1 and r.get_by_invoice_number("I1").billing_account.id==1 and r.list_by_organization_id(1)==[a] and r.list_by_subscription_id(1)==[a] and r.list_by_status("draft")==[a] and r.list_due_before(datetime(2026,2,1,tzinfo=timezone.utc))==[] and a.line_items[0].invoice.id==a.id
def test_missing_rollback_and_conflicts(s):
 r=SqlAlchemyInvoiceRepository(s);assert r.get_by_id(99) is None and r.get_by_invoice_number("x") is None and r.list_by_organization_id(99)==[];a=r.save(inv());i=a.id;s.rollback();assert r.get_by_id(i) is None
 a=r.save(inv());s.commit()
 with pytest.raises(BillingPersistenceConflictError):r.save(inv())
 s.rollback();s.add(InvoiceLineItem(invoice_id=a.id,line_number=1,item_type="usage",description="x",quantity=1,unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1));s.commit();b=inv("I2");r.save(b);s.flush();s.add(InvoiceLineItem(invoice_id=b.id,line_number=1,item_type="usage",description="x",quantity=1,unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1));s.commit();assert not hasattr(r,"delete") and not hasattr(r,"commit")
