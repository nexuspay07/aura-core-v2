from datetime import datetime,timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import *

@pytest.fixture
def s():
 e=create_engine("sqlite:///:memory:");event.listen(e,"connect",lambda d,_:d.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);x=sessionmaker(bind=e)();x.execute(insert(user_table).values(id=1,email="i@test",password_hash="x"));x.execute(insert(organization_table).values(id=1,name="o",slug="inv",owner_user_id=1,plan="free",subscription_status="inactive",is_active=True));x.add(Plan(id=1,code="p",name="P",seat_limit=1));x.flush();x.add_all([BillingAccount(id=1,organization_id=1,billing_email="a@test",billing_name="A",country_code="CA",currency="CAD"),Subscription(id=1,organization_id=1,plan_id=1,status="active",billing_cycle="monthly",starts_at=datetime.now(timezone.utc))]);x.commit();yield x
def invoice(n="I1"):
 return Invoice(organization_id=1,billing_account_id=1,subscription_id=1,invoice_number=n,status="draft",currency="CAD",period_start=datetime(2026,1,1,tzinfo=timezone.utc),period_end=datetime(2026,2,1,tzinfo=timezone.utc))
def test_invoice_and_line_relationships(s):
 i=invoice();s.add(i);s.flush();s.add_all([InvoiceLineItem(invoice_id=i.id,line_number=2,item_type="usage",description="b",quantity=Decimal("1"),unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1),InvoiceLineItem(invoice_id=i.id,line_number=1,item_type="usage",description="a",quantity=Decimal("1"),unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1)]);s.commit();assert [x.line_number for x in i.line_items]==[1,2] and i.organization.invoices[0].id==i.id and i.billing_account.invoices[0].id==i.id and i.subscription.invoices[0].id==i.id
def test_constraints(s):
 s.add(invoice());s.commit();s.add(invoice())
 with pytest.raises(Exception):s.commit()
 s.rollback()
