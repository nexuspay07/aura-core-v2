from datetime import datetime,timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import *
from app.commercial.invoice_service import *
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
@pytest.fixture
def s():
 e=create_engine("sqlite:///:memory:");event.listen(e,"connect",lambda d,_:d.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);x=sessionmaker(bind=e)();x.execute(insert(user_table).values(id=1,email="x@i",password_hash="x"));x.execute(insert(organization_table).values(id=1,name="o",slug="is",owner_user_id=1,plan="free",subscription_status="inactive",is_active=True));x.add(Plan(id=1,code="p",name="p",seat_limit=1));x.flush();x.add_all([BillingAccount(id=1,organization_id=1,billing_email="a@i",billing_name="a",country_code="CA",currency="CAD"),Subscription(id=1,organization_id=1,plan_id=1,status="active",billing_cycle="monthly",starts_at=NOW)]);x.commit();yield x
def make(s,n="I"):
 return InvoiceService(s,clock=lambda:NOW).create_invoice(organization_id=1,billing_account_id=1,subscription_id=1,invoice_number=n,currency="CAD",period_start=NOW,period_end=datetime(2026,2,1,tzinfo=timezone.utc),amount_due=Decimal("10"))
def line(s,i):return InvoiceService(s).add_line_item(i.id,line_number=1,item_type="usage",description="x",quantity=Decimal("1"),unit_amount=Decimal("10"),subtotal_amount=Decimal("10"),tax_amount=Decimal("0"),discount_amount=Decimal("0"),total_amount=Decimal("10"))
def test_create_line_issue_payment_lifecycle(s):
 i=make(s);assert i.status=="draft" and i.amount_paid==0 and s.in_transaction();line(s,i);InvoiceService(s,clock=lambda:NOW).issue_invoice(i.id);assert i.status=="open" and i.issued_at==NOW;InvoiceService(s,clock=lambda:NOW).record_payment(i.id,Decimal("10"));assert i.status=="paid" and i.paid_at==NOW;s.commit()
def test_validation_void_uncollectible_and_rollback(s):
 svc=InvoiceService(s)
 with pytest.raises(InvoiceInputError):svc.create_invoice(organization_id=1,billing_account_id=1,subscription_id=1,invoice_number="",currency="cad",period_start=NOW,period_end=NOW)
 i=make(s);svc.void_invoice(i.id);assert i.status=="void";s.rollback();assert s.get(Invoice,i.id) is None
def test_transitions(s):
 i=make(s);line(s,i);InvoiceService(s).issue_invoice(i.id);InvoiceService(s).mark_uncollectible(i.id);assert i.status=="uncollectible"
 with pytest.raises(InvoiceTransitionError):InvoiceService(s).void_invoice(i.id)
