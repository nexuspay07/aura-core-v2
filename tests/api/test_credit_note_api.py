from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.credit_note_routes import router,current
import pytest
from datetime import datetime,timezone,timedelta
from sqlalchemy import create_engine,event,insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import Plan,BillingAccount,Subscription,Invoice,CreditNote,CreditNoteLineItem
import app.api.credit_note_routes as routes
def client():
 a=FastAPI();a.include_router(router);a.dependency_overrides[current]=lambda:{'organization':{'id':1}};return TestClient(a)
def test_openapi_credit_note_routes_and_schemas():
 s=client().get('/openapi.json').json();assert '/commercial/credit-notes' in s['paths'];assert 'CreditNoteCreate' in s['components']['schemas'];assert 'CreditNoteOut' in s['components']['schemas']
def test_credit_note_authentication_required():
 a=FastAPI();a.include_router(router);assert TestClient(a).get('/commercial/credit-notes').status_code==403
def test_invalid_credit_note_token_is_rejected():
 a=FastAPI();a.include_router(router);assert TestClient(a).get('/commercial/credit-notes',headers={'Authorization':'Bearer invalid'}).status_code==401

@pytest.fixture
def api(monkeypatch):
 e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);F=sessionmaker(bind=e,expire_on_commit=False);s=F();s.execute(insert(user_table),[{'id':1,'email':'cn1@test','password_hash':'x'},{'id':2,'email':'cn2@test','password_hash':'x'}]);s.execute(insert(organization_table),[{'id':1,'name':'one','slug':'cn-one','owner_user_id':1,'plan':'free','subscription_status':'inactive','is_active':True},{'id':2,'name':'two','slug':'cn-two','owner_user_id':2,'plan':'free','subscription_status':'inactive','is_active':True}]);n=datetime(2026,1,1,tzinfo=timezone.utc);s.add(Plan(id=1,code='cn',name='cn',seat_limit=1));s.add_all([BillingAccount(id=1,organization_id=1,billing_email='a@a',billing_name='a',country_code='CA',currency='CAD'),BillingAccount(id=2,organization_id=2,billing_email='b@b',billing_name='b',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=n),Subscription(id=2,organization_id=2,plan_id=1,status='active',billing_cycle='monthly',starts_at=n)]);s.flush();s.add_all([Invoice(id=1,organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='CI1',status='open',currency='CAD',period_start=n,period_end=n+timedelta(days=31),subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1,amount_due=1,amount_paid=0),Invoice(id=2,organization_id=2,billing_account_id=2,subscription_id=2,invoice_number='CI2',status='open',currency='CAD',period_start=n,period_end=n+timedelta(days=31),subtotal_amount=1,tax_amount=0,discount_amount=0,total_amount=1,amount_due=1,amount_paid=0)]);s.commit();a=FastAPI();a.include_router(router);a.dependency_overrides[current]=lambda:{'organization':{'id':1}};monkeypatch.setattr(routes,'SessionLocal',F);yield TestClient(a),F,n;s.close();e.dispose()
def test_create_list_retrieve_and_tenant_isolation(api):
 c,F,n=api;r=c.post('/commercial/credit-notes',json={'organization_id':2,'invoice_id':1,'credit_note_number':'CN-API','currency':'CAD','reason':'x'});assert r.status_code==201 and r.json()['organization_id']==1;fresh=F();x=fresh.get(CreditNote,r.json()['id']);assert x and x.organization_id==1;fresh.close();assert len(c.get('/commercial/credit-notes').json())==1;assert c.get(f'/commercial/credit-notes/{x.id}').status_code==200

def note_with_line(F,n,org=1,number='CN-LINE'):
 s=F();x=CreditNote(organization_id=org,invoice_id=org,credit_note_number=number,status='draft',currency='CAD',subtotal=1,tax=0,total=1,amount_applied=0,amount_remaining=1,created_at=n,updated_at=n);s.add(x);s.flush();s.add(CreditNoteLineItem(credit_note_id=x.id,line_number=1,description='x',quantity=1,unit_amount=1,subtotal=1,tax=0,total=1,created_at=n));s.commit();i=x.id;s.close();return i
def test_retrieve_update_unknown_and_cross_tenant(api):
 c,F,n=api;i=note_with_line(F,n);other=note_with_line(F,n,2,'CN-OTHER')
 assert c.get('/commercial/credit-notes/999').status_code==404 and c.get(f'/commercial/credit-notes/{other}').status_code==404
 assert c.patch(f'/commercial/credit-notes/{i}',json={'reason':'updated'}).status_code==200;fresh=F();assert fresh.get(CreditNote,i).reason=='updated';fresh.close()
 assert c.patch(f'/commercial/credit-notes/{other}',json={'reason':'no'}).status_code==404
def test_issue_void_and_invalid_transitions_persist(api):
 c,F,n=api;i=note_with_line(F,n);assert c.post(f'/commercial/credit-notes/{i}/issue').json()['status']=='issued';fresh=F();assert fresh.get(CreditNote,i).status=='issued';fresh.close();assert c.post(f'/commercial/credit-notes/{i}/issue').status_code==409
 assert c.post(f'/commercial/credit-notes/{i}/void').json()['status']=='void';fresh=F();assert fresh.get(CreditNote,i).status=='void';fresh.close();assert c.post(f'/commercial/credit-notes/{i}/void').status_code==409

@pytest.mark.parametrize('operation',['create','update','issue','void'])
def test_credit_note_write_failure_rolls_back(operation,api,monkeypatch):
 c,F,n=api;c=TestClient(c.app,raise_server_exceptions=False);i=note_with_line(F,n,number=f'CN-ROLL-{operation}')
 class Broken:
  def __init__(self):self.inner=F();self.rolled=False
  def __getattr__(self,k):return getattr(self.inner,k)
  def commit(self):raise RuntimeError('forced')
  def rollback(self):self.rolled=True;self.inner.rollback()
  def close(self):self.inner.close()
 broken=Broken();monkeypatch.setattr(routes,'SessionLocal',lambda:broken)
 if operation=='create':r=c.post('/commercial/credit-notes',json={'invoice_id':1,'credit_note_number':'CN-FAIL','currency':'CAD'});expected=None
 elif operation=='update':r=c.patch(f'/commercial/credit-notes/{i}',json={'reason':'changed'});expected='draft'
 elif operation=='issue':r=c.post(f'/commercial/credit-notes/{i}/issue');expected='draft'
 else:
  monkeypatch.setattr(routes,'SessionLocal',F);assert TestClient(c.app).post(f'/commercial/credit-notes/{i}/issue').status_code==200;monkeypatch.setattr(routes,'SessionLocal',lambda:broken);r=c.post(f'/commercial/credit-notes/{i}/void');expected='issued'
 assert r.status_code>=500 and broken.rolled
 fresh=F()
 if operation=='create':assert fresh.query(CreditNote).filter_by(credit_note_number='CN-FAIL').first() is None
 else:assert fresh.get(CreditNote,i).status==expected
 fresh.close()
