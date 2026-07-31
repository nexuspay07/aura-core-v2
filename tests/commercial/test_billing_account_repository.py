import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.db.organization_orm import Organization
from app.commercial.models import BillingAccount
from app.commercial.repositories import SqlAlchemyBillingAccountRepository
from app.commercial.billing import BillingPersistenceConflictError

@pytest.fixture
def session():
 e=create_engine("sqlite:///:memory:");event.listen(e,"connect",lambda d,_:d.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);s=sessionmaker(bind=e)();s.execute(insert(user_table).values(id=1,email="r@test.com",password_hash="x"));s.execute(insert(organization_table),[{"id":1,"name":"o","slug":"repo-bill","owner_user_id":1,"plan":"free","subscription_status":"inactive","is_active":True},{"id":2,"name":"p","slug":"repo-bill-2","owner_user_id":1,"plan":"free","subscription_status":"inactive","is_active":True}]);s.commit();yield s
def account(**v):
 x=dict(organization_id=1,billing_email="a@test.com",billing_name="A",country_code="CA",currency="CAD");x.update(v);return BillingAccount(**x)
def test_save_get_relationships_and_no_commit(session):
 r=SqlAlchemyBillingAccountRepository(session);a=r.save(account());assert session.in_transaction();session.commit();assert r.get_by_id(a.id).organization.id==1 and session.get(Organization,1).billing_account.id==a.id and not isinstance(session.get(Organization,1).billing_account,list)
def test_missing_list_order_and_no_update_delete(session):
 r=SqlAlchemyBillingAccountRepository(session);assert r.get_by_id(99) is None and r.get_by_organization_id(99) is None and r.list_by_status("active")==[];assert not hasattr(r,"update") and not hasattr(r,"delete")
def test_duplicate_rollback_and_parent_preserved(session):
 r=SqlAlchemyBillingAccountRepository(session);a=r.save(account());session.commit()
 with pytest.raises(BillingPersistenceConflictError):r.save(account(billing_email="b@test.com"))
 session.rollback();session.delete(a);session.commit();assert session.get(Organization,1) is not None
def test_caller_rollback_removes(session):
 r=SqlAlchemyBillingAccountRepository(session);a=r.save(account());i=a.id;session.rollback();assert r.get_by_id(i) is None
def test_status_lists_filter_and_order(session):
 r=SqlAlchemyBillingAccountRepository(session);first=r.save(account(billing_email="z@test.com"));second=r.save(account(organization_id=2,billing_email="a@test.com",billing_status="suspended"));session.commit()
 assert [x.id for x in r.list_by_status("active")]==[first.id]
 assert [x.id for x in r.list_by_status("suspended")]==[second.id]
 assert r.list_by_status("closed")==[]
def test_foreign_key_and_parent_delete_restricted(session):
 r=SqlAlchemyBillingAccountRepository(session)
 with pytest.raises(BillingPersistenceConflictError):r.save(account(organization_id=999))
 session.rollback();a=r.save(account());session.commit();session.delete(session.get(Organization,1))
 with pytest.raises(Exception):session.commit()
