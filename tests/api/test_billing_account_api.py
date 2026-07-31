from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
import app.api.billing_account_routes as routes
from app.api.billing_account_routes import router,current
from app.commercial.models import BillingAccount
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table

def data(**x):
 d={"organization_id":2,"billing_email":"billing@example.test","billing_name":"Billing","country_code":"CA","currency":"CAD","address_line_1":"One Street"};d.update(x);return d

@pytest.fixture
def api(monkeypatch):
 e=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool);event.listen(e,"connect",lambda c,_:c.execute("PRAGMA foreign_keys=ON"));Base.metadata.create_all(e);F=sessionmaker(bind=e,expire_on_commit=False);s=F();s.execute(insert(user_table),[{"id":1,"email":"one@test","password_hash":"x"},{"id":2,"email":"two@test","password_hash":"x"}]);s.execute(insert(organization_table),[{"id":1,"name":"one","slug":"ba-one","owner_user_id":1,"plan":"free","subscription_status":"inactive","is_active":True},{"id":2,"name":"two","slug":"ba-two","owner_user_id":2,"plan":"free","subscription_status":"inactive","is_active":True}]);s.commit();a=FastAPI();a.include_router(router);a.dependency_overrides[current]=lambda:{"organization":{"id":1}};monkeypatch.setattr(routes,"SessionLocal",F);yield TestClient(a,raise_server_exceptions=False),F,a;s.close();e.dispose()

def create(c,**x):
 r=c.post("/commercial/billing-accounts",json=data(**x));assert r.status_code==201,r.text;return r.json()

def test_openapi_and_authentication():
 a=FastAPI();a.include_router(router);c=TestClient(a);schema=c.get("/openapi.json").json();assert "/commercial/billing-accounts" in schema["paths"] and "BillingAccountCreate" in schema["components"]["schemas"];assert c.get("/commercial/billing-accounts").status_code==403;assert c.get("/commercial/billing-accounts",headers={"Authorization":"Bearer invalid"}).status_code==401;assert c.get("/commercial/billing-accounts",headers={"Authorization":"bad"}).status_code==403

def test_create_list_retrieve_and_fresh_persistence(api):
 c,F,_=api;x=create(c);s=F();stored=s.get(BillingAccount,x["id"]);assert x["organization_id"]==stored.organization_id==1 and stored.billing_status=="active";s.close();assert c.get("/commercial/billing-accounts").json()[0]["id"]==x["id"];assert c.get(f"/commercial/billing-accounts/{x['id']}").status_code==200

@pytest.mark.parametrize("change",[{"currency":"cad"},{"country_code":"can"},{"billing_email":"bad"}])
def test_create_validation_and_duplicate_rejection(api,change):
 c,F,_=api;assert c.post("/commercial/billing-accounts",json=data(**change)).status_code==409;s=F();assert s.query(BillingAccount).count()==0;s.close();create(c);assert c.post("/commercial/billing-accounts",json=data(billing_email="other@test")).status_code==409

def test_cross_org_retrieval_update_and_status_are_blocked(api):
 c,F,_=api;s=F();other=BillingAccount(organization_id=2,billing_email="two@test",billing_name="Two",country_code="CA",currency="CAD");s.add(other);s.commit();i=other.id;s.close();assert c.get(f"/commercial/billing-accounts/{i}").status_code==404;assert c.patch(f"/commercial/billing-accounts/{i}",json={"billing_name":"x"}).status_code==404;assert c.post(f"/commercial/billing-accounts/{i}/suspend").status_code==404

def test_update_and_lifecycle_persist(api):
 c,F,_=api;x=create(c);r=c.patch(f"/commercial/billing-accounts/{x['id']}",json={"organization_id":2,"billing_name":" Changed ","currency":"USD"});assert r.status_code==200 and r.json()["billing_name"]=="Changed";assert c.post(f"/commercial/billing-accounts/{x['id']}/suspend").json()["billing_status"]=="suspended";assert c.post(f"/commercial/billing-accounts/{x['id']}/activate").json()["billing_status"]=="active";assert c.post(f"/commercial/billing-accounts/{x['id']}/close").json()["billing_status"]=="closed";s=F();assert s.get(BillingAccount,x['id']).billing_status=="closed";s.close();assert c.post(f"/commercial/billing-accounts/{x['id']}/close").status_code==409

@pytest.mark.parametrize("operation,initial,endpoint",[("update","active",None),("activate","suspended","activate"),("suspend","active","suspend"),("close","active","close")])
def test_commit_failure_rolls_back_existing_write(api,monkeypatch,operation,initial,endpoint):
 c,F,_=api;x=create(c);s=F();account=s.get(BillingAccount,x["id"]);account.billing_status=initial;s.commit();s.close()
 class Broken:
  def __init__(self):self.inner=F();self.rolled=False
  def __getattr__(self,key):return getattr(self.inner,key)
  def commit(self):raise RuntimeError("forced commit failure")
  def rollback(self):self.rolled=True;self.inner.rollback()
  def close(self):self.inner.close()
 broken=Broken();monkeypatch.setattr(routes,"SessionLocal",lambda:broken)
 response=c.patch(f"/commercial/billing-accounts/{x['id']}",json={"billing_name":"Mutated","city":"Changed"}) if operation=="update" else c.post(f"/commercial/billing-accounts/{x['id']}/{endpoint}")
 assert response.status_code>=500 and broken.rolled
 s=F();stored=s.get(BillingAccount,x["id"]);assert stored.billing_status==initial and stored.organization_id==1
 if operation=="update":assert stored.billing_name=="Billing" and stored.city is None
 s.close()

def test_commit_failure_rolls_back_create_without_duplicate_residue(api,monkeypatch):
 c,F,_=api
 class Broken:
  def __init__(self):self.inner=F();self.rolled=False
  def __getattr__(self,key):return getattr(self.inner,key)
  def commit(self):raise RuntimeError("forced commit failure")
  def rollback(self):self.rolled=True;self.inner.rollback()
  def close(self):self.inner.close()
 broken=Broken();monkeypatch.setattr(routes,"SessionLocal",lambda:broken);response=c.post("/commercial/billing-accounts",json=data());assert response.status_code>=500 and broken.rolled
 s=F();assert s.query(BillingAccount).count()==0;s.close();monkeypatch.setattr(routes,"SessionLocal",F);assert create(c)["organization_id"]==1
