from datetime import datetime,timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,event,insert
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import pytest
import app.api.usage_meter_routes as routes
from app.api.usage_meter_routes import router,current
from app.db.database import Base
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.commercial.models import Plan,PlanFeature,Subscription,UsageRecord
NOW=datetime(2026,1,2,tzinfo=timezone.utc)
@pytest.fixture
def api(monkeypatch):
 e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);F=sessionmaker(bind=e,expire_on_commit=False);s=F();s.execute(insert(user_table),[{'id':1,'email':'u1@test','password_hash':'x'},{'id':2,'email':'u2@test','password_hash':'x'}]);s.execute(insert(organization_table),[{'id':1,'name':'one','slug':'usage-one','owner_user_id':1,'plan':'free','subscription_status':'inactive','is_active':True},{'id':2,'name':'two','slug':'usage-two','owner_user_id':2,'plan':'free','subscription_status':'inactive','is_active':True}]);s.add(Plan(id=1,code='usage',name='Usage',seat_limit=1));s.add(PlanFeature(plan_id=1,feature_key='calls',value_type='integer',integer_value=10));s.add_all([Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=NOW),Subscription(id=2,organization_id=2,plan_id=1,status='active',billing_cycle='monthly',starts_at=NOW)]);s.commit();a=FastAPI();a.include_router(router);a.dependency_overrides[current]=lambda:{'organization':{'id':1}};monkeypatch.setattr(routes,'SessionLocal',F);yield TestClient(a,raise_server_exceptions=False),F;s.close();e.dispose()
def body(**x):
 d={'organization_id':2,'feature_key':'calls','quantity':'2','unit':'request','occurred_at':NOW.isoformat(),'idempotency_key':'key-1'};d.update(x);return d
def test_openapi_and_authentication():
 a=FastAPI();a.include_router(router);c=TestClient(a);schema=c.get('/openapi.json').json();assert '/commercial/usage' in schema['paths'] and '/commercial/usage/{record_id}' in schema['paths'] and 'UsageCreate' in schema['components']['schemas'];assert c.get('/commercial/usage').status_code==403;assert c.get('/commercial/usage',headers={'Authorization':'Bearer invalid'}).status_code==401;assert c.get('/commercial/usage',headers={'Authorization':'bad'}).status_code==403
def test_record_list_retrieve_fresh_and_org_isolation(api):
 c,F=api;r=c.post('/commercial/usage',json=body());assert r.status_code==201 and r.json()['organization_id']==1;i=r.json()['id'];s=F();assert s.get(UsageRecord,i).subscription_id==1;s.add(UsageRecord(organization_id=2,subscription_id=2,feature_key='calls',quantity=1,unit='r',occurred_at=NOW,idempotency_key='other'));s.commit();other=s.query(UsageRecord).filter_by(organization_id=2).one().id;s.close();assert [x['id'] for x in c.get('/commercial/usage').json()]==[i];assert c.get(f'/commercial/usage/{other}').status_code==404 and c.get('/commercial/usage/999').status_code==404
@pytest.mark.parametrize('change',[{'quantity':'0'},{'quantity':'-1'},{'feature_key':'missing'},{'occurred_at':'invalid'}])
def test_validation_and_no_partial_record(api,change):
 c,F=api;assert c.post('/commercial/usage',json=body(**change)).status_code in {409,422};s=F();assert s.query(UsageRecord).count()==0;s.close()
def test_idempotency_and_commit_rollback(api,monkeypatch):
 c,F=api;first=c.post('/commercial/usage',json=body()).json();assert c.post('/commercial/usage',json=body()).json()['id']==first['id']
 class Broken:
  def __init__(self):self.i=F();self.rolled=False
  def __getattr__(self,k):return getattr(self.i,k)
  def commit(self):raise RuntimeError()
  def rollback(self):self.rolled=True;self.i.rollback()
  def close(self):self.i.close()
 b=Broken();monkeypatch.setattr(routes,'SessionLocal',lambda:b);assert c.post('/commercial/usage',json=body(idempotency_key='failed')).status_code>=500 and b.rolled;s=F();assert s.query(UsageRecord).count()==1;s.close();monkeypatch.setattr(routes,'SessionLocal',F);assert c.post('/commercial/usage',json=body(idempotency_key='later')).status_code==201
