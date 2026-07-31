from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.billing import *

NOW=datetime(2026,1,1,tzinfo=timezone.utc)
@pytest.fixture
def session():
 e=create_engine("sqlite:///:memory:");event.listen(e,"connect",lambda d,_:d.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);s=sessionmaker(bind=e)();s.execute(insert(user_table).values(id=1,email="b@test.com",password_hash="x"));s.execute(insert(organization_table).values(id=1,name="o",slug="bill",owner_user_id=1,plan="free",subscription_status="inactive",is_active=True));s.commit();yield s
def values(**kw):
 v=dict(organization_id=1,billing_email=" a@EXAMPLE.com ",billing_name=" Name ",country_code="CA",currency="CAD");v.update(kw);return v
def service(s,now=NOW):return BillingAccountService(s,clock=lambda:now)
def create(s):return service(s).create_billing_account(**values())

def test_valid_creation_defaults_trim_clock_and_no_commit(session):
 a=create(session);assert (a.billing_email,a.billing_name,a.billing_status,a.version,a.created_at,a.updated_at)==("a@EXAMPLE.com","Name","active",1,NOW,NOW);assert session.in_transaction()
def test_missing_and_duplicate_rejected(session):
 with pytest.raises(BillingAccountNotFoundError):service(session).create_billing_account(**values(organization_id=99))
 create(session);session.commit()
 with pytest.raises(BillingAccountAlreadyExistsError):create(session)
@pytest.mark.parametrize("field,value,error",[("billing_email","",InvalidBillingEmailError),("billing_email","bad",InvalidBillingEmailError),("billing_name","",InvalidBillingNameError),("billing_name"," ",InvalidBillingNameError),("country_code","ca",InvalidCountryCodeError),("country_code","CAN",InvalidCountryCodeError),("currency","cad",InvalidCurrencyError),("currency","CA",InvalidCurrencyError)])
def test_validation(session,field,value,error):
 with pytest.raises(error):service(session).create_billing_account(**values(**{field:value}))
def test_update_fields_version_and_rollback(session):
 a=create(session);session.commit();created=a.created_at
 b=service(session,NOW.replace(day=2)).update_billing_details(a.id,billing_name=" New ",billing_email="new@X.com",address_line_1="One",country_code="US",currency="USD")
 assert (b.billing_name,b.billing_email,b.address_line_1,b.country_code,b.currency,b.version,b.created_at)==("New","new@X.com","One","US","USD",2,created)
 session.rollback();assert session.get(type(a),a.id).billing_name=="Name"
def test_status_transitions_and_subscription_unchanged(session):
 a=create(session);session.commit();service(session).change_billing_status(a.id,"suspended");service(session).change_billing_status(a.id,"active");service(session).change_billing_status(a.id,"closed");assert a.version==4
 with pytest.raises(InvalidBillingStatusTransitionError):service(session).change_billing_status(a.id,"active")
 with pytest.raises(InvalidBillingStatusError):service(session).change_billing_status(a.id,"bad")
def test_commit_and_rollback_creation(session):
 a=create(session);i=a.id;session.rollback();assert session.get(type(a),i) is None
 a=create(session);session.commit();assert session.get(type(a),a.id) is not None
def test_injected_failure_maps_and_rolls_back(session,monkeypatch):
 svc=service(session);monkeypatch.setattr(svc.repo,"save",lambda _:(_ for _ in ()).throw(RuntimeError("db")))
 with pytest.raises(BillingPersistenceConflictError):svc.create_billing_account(**values())
 assert svc.repo.get_by_organization_id(1) is None
