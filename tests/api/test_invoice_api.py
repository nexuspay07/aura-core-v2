from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.invoice_routes import router,get_session,current
from datetime import datetime,timezone
from decimal import Decimal
import app.api.invoice_routes as routes
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine,event,insert
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import Plan,BillingAccount,Subscription,Invoice,InvoiceLineItem
def app_client():
 app=FastAPI();app.include_router(router);app.dependency_overrides[current]=lambda:{'id':1};return TestClient(app)
def test_openapi_registers_invoice_routes_and_schemas():
 schema=app_client().get('/openapi.json').json();assert '/commercial/invoices' in schema['paths'];assert 'InvoiceCreate' in schema['components']['schemas'];assert 'InvoiceOut' in schema['components']['schemas']
def test_authentication_failure():
 app=FastAPI();app.include_router(router);assert TestClient(app).get('/commercial/invoices').status_code==403
def test_invalid_path_and_body_validation():
 c=app_client();assert c.get('/commercial/invoices/nope').status_code==422;assert c.post('/commercial/invoices',json={}).status_code==422

class FakeSession:
 def __init__(self):self.commits=0;self.rollbacks=0
 def commit(self):self.commits+=1
 def rollback(self):self.rollbacks+=1
 def refresh(self,x):pass
 def close(self):pass
 def flush(self):pass
def invoice(i,org=1,status='open'):
 return SimpleNamespace(id=i,organization_id=org,invoice_number=f'I-{i}',status=status,currency='CAD',amount_due=Decimal('10'),amount_paid=Decimal('0'),version=1,due_at=None)
def test_listing_and_tenant_retrieval(monkeypatch):
 ours,other=invoice(1),invoice(2,2)
 class Repo:
  def __init__(self,s):pass
  def list_by_organization_id(self,o):return [ours] if o==1 else []
  def get_by_id(self,i):return {1:ours,2:other}.get(i)
 monkeypatch.setattr(routes,'SqlAlchemyInvoiceRepository',Repo);s=FakeSession();app=FastAPI();app.include_router(router);app.dependency_overrides[current]=lambda:{'organization':{'id':1}};app.dependency_overrides[get_session]=lambda:s;c=TestClient(app)
 assert [x['id'] for x in c.get('/commercial/invoices').json()]==[1]
 assert c.get('/commercial/invoices/1').status_code==200 and c.get('/commercial/invoices/2').status_code==404 and c.get('/commercial/invoices/99').status_code==404
def test_update_uses_commit_and_cross_tenant_is_blocked(monkeypatch):
 ours,other=invoice(1),invoice(2,2)
 class Repo:
  def __init__(self,s):pass
  def get_by_id(self,i):return {1:ours,2:other}.get(i)
 monkeypatch.setattr(routes,'SqlAlchemyInvoiceRepository',Repo);s=FakeSession();app=FastAPI();app.include_router(router);app.dependency_overrides[current]=lambda:{'organization':{'id':1}};app.dependency_overrides[get_session]=lambda:s;c=TestClient(app)
 assert c.patch('/commercial/invoices/1',json={'currency':'USD'}).status_code==200 and ours.currency=='USD' and s.commits==1
 assert c.patch('/commercial/invoices/2',json={'currency':'USD'}).status_code==404
def test_openapi_has_all_invoice_operations():
 paths=app_client().get('/openapi.json').json()['paths'];assert set(paths['/commercial/invoices'])=={'get','post'};assert {'get','patch'}<=set(paths['/commercial/invoices/{invoice_id}']);assert '/commercial/invoices/{invoice_id}/issue' in paths and '/commercial/invoices/{invoice_id}/void' in paths

def test_invalid_token_is_rejected_by_real_authentication():
 app=FastAPI();app.include_router(router);assert TestClient(app).get('/commercial/invoices',headers={'Authorization':'Bearer invalid'}).status_code==401

@pytest.fixture
def real_api(monkeypatch):
 e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);Factory=sessionmaker(bind=e,expire_on_commit=False);s=Factory();s.execute(insert(user_table),[{'id':1,'email':'api1@test','password_hash':'x'},{'id':2,'email':'api2@test','password_hash':'x'}]);s.execute(insert(organization_table),[{'id':1,'name':'one','slug':'api-one','owner_user_id':1,'plan':'free','subscription_status':'inactive','is_active':True},{'id':2,'name':'two','slug':'api-two','owner_user_id':2,'plan':'free','subscription_status':'inactive','is_active':True}]);now=datetime(2026,1,1,tzinfo=timezone.utc);s.add(Plan(id=1,code='api',name='api',seat_limit=1));s.add_all([BillingAccount(id=1,organization_id=1,billing_email='a@a',billing_name='a',country_code='CA',currency='CAD'),BillingAccount(id=2,organization_id=2,billing_email='b@b',billing_name='b',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=now),Subscription(id=2,organization_id=2,plan_id=1,status='active',billing_cycle='monthly',starts_at=now)]);s.commit();app=FastAPI();app.include_router(router);app.dependency_overrides[current]=lambda:{'organization':{'id':1}};monkeypatch.setattr(routes,'SessionLocal',Factory);yield TestClient(app),Factory,now;s.close();e.dispose()
def payload(now,org=2):return {'organization_id':org,'billing_account_id':1,'subscription_id':1,'invoice_number':'API-CREATE','currency':'CAD','period_start':now.isoformat(),'period_end':(now.replace(month=2)).isoformat(),'subtotal_amount':'10','tax_amount':'0','discount_amount':'0','total_amount':'10','amount_due':'10','amount_paid':'0'}
def test_create_uses_authenticated_org_and_persists_fresh_session(real_api):
 c,F,n=real_api;r=c.post('/commercial/invoices',json=payload(n));assert r.status_code==201 and r.json()['organization_id']==1;fresh=F();x=fresh.get(Invoice,r.json()['id']);assert x and x.organization_id==1 and x.invoice_number=='API-CREATE';fresh.close()
def test_issue_void_and_tenant_blocking_with_fresh_sessions(real_api):
 c,F,n=real_api;s=F();draft=Invoice(organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='API-DRAFT',status='draft',currency='CAD',period_start=n,period_end=n.replace(month=2),subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1,amount_due=1,amount_paid=0);s.add(draft);s.flush();s.add(InvoiceLineItem(invoice_id=draft.id,line_number=1,item_type='adjustment',description='x',quantity=1,unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1));other=Invoice(organization_id=2,billing_account_id=2,subscription_id=2,invoice_number='API-OTHER',status='draft',currency='CAD',period_start=n,period_end=n.replace(month=2),subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1,amount_due=1,amount_paid=0);s.add(other);s.commit();did=draft.id;oid=other.id;s.close();assert c.post(f'/commercial/invoices/{did}/issue').json()['status']=='open';fresh=F();assert fresh.get(Invoice,did).status=='open';fresh.close();assert c.post(f'/commercial/invoices/{did}/void').json()['status']=='void';fresh=F();assert fresh.get(Invoice,did).status=='void';fresh.close();assert c.post(f'/commercial/invoices/{oid}/issue').status_code==404 and c.post(f'/commercial/invoices/{oid}/void').status_code==404

@pytest.mark.parametrize('operation', ['create','update','issue','void'])
def test_router_write_failure_rolls_back(operation, real_api, monkeypatch):
 c,F,n=real_api;c=TestClient(c.app,raise_server_exceptions=False);s=F();x=Invoice(organization_id=1,billing_account_id=1,subscription_id=1,invoice_number=f'ROLL-{operation}',status='draft',currency='CAD',period_start=n,period_end=n.replace(month=2),subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1,amount_due=1,amount_paid=0);s.add(x);s.flush();s.add(InvoiceLineItem(invoice_id=x.id,line_number=1,item_type='adjustment',description='x',quantity=1,unit_amount=1,subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1));s.commit();identifier=x.id;s.close()
 class BrokenSession:
  def __init__(self):self.inner=F();self.rolled=False
  def __getattr__(self,k):return getattr(self.inner,k)
  def commit(self):raise RuntimeError('forced commit failure')
  def rollback(self):self.rolled=True;self.inner.rollback()
  def close(self):self.inner.close()
 broken=BrokenSession();monkeypatch.setattr(routes,'SessionLocal',lambda:broken)
 if operation=='create': response=c.post('/commercial/invoices',json=payload(n));number='API-CREATE'
 elif operation=='update': response=c.patch(f'/commercial/invoices/{identifier}',json={'currency':'USD'});number=None
 elif operation=='issue': response=c.post(f'/commercial/invoices/{identifier}/issue');number=None
 else: response=c.post(f'/commercial/invoices/{identifier}/void');number=None
 assert response.status_code>=500 and broken.rolled
 fresh=F()
 if operation=='create': assert fresh.query(Invoice).filter_by(invoice_number=number).first() is None
 else: assert fresh.get(Invoice,identifier).status=='draft' and fresh.get(Invoice,identifier).currency=='CAD'
 fresh.close()
