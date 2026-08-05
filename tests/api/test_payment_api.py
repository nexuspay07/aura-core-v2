from datetime import datetime, timezone
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.api.payment_routes as routes
from app.api.payment_routes import current, router
from app.commercial.models import BillingAccount, Invoice, Plan, Subscription
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
@pytest.fixture
def client(monkeypatch):
 e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);event.listen(e,'connect',lambda c,_:c.execute('PRAGMA foreign_keys=ON'));Base.metadata.create_all(e);F=sessionmaker(bind=e,expire_on_commit=False);s=F();s.execute(insert(user_table),[{'id':1,'email':'papi@test','password_hash':'x'},{'id':2,'email':'papi2@test','password_hash':'x'}]);s.execute(insert(organization_table),[{'id':1,'name':'one','slug':'papi-one','owner_user_id':1,'plan':'free','subscription_status':'inactive','is_active':True},{'id':2,'name':'two','slug':'papi-two','owner_user_id':2,'plan':'free','subscription_status':'inactive','is_active':True}]);s.add(Plan(id=1,code='papi',name='P',seat_limit=1));s.add_all([BillingAccount(id=1,organization_id=1,billing_email='x@x',billing_name='x',country_code='CA',currency='CAD'),Subscription(id=1,organization_id=1,plan_id=1,status='active',billing_cycle='monthly',starts_at=NOW)]);s.flush();s.add_all([Invoice(id=1,organization_id=1,billing_account_id=1,subscription_id=1,invoice_number='PAPI-1',status='open',currency='CAD',period_start=NOW,period_end=datetime(2026,2,1,tzinfo=timezone.utc),total_amount=10,amount_due=10),Invoice(id=2,organization_id=2,billing_account_id=1,subscription_id=1,invoice_number='PAPI-2',status='open',currency='CAD',period_start=NOW,period_end=datetime(2026,2,1,tzinfo=timezone.utc),total_amount=10,amount_due=10)]);s.commit();app=FastAPI();app.include_router(router);app.dependency_overrides[current]=lambda:{'organization':{'id':1}};monkeypatch.setattr(routes,'SessionLocal',F);yield TestClient(app)
def test_create_retrieve_isolation_and_openapi(client):
 body={'provider':'fake','idempotency_key':'payment-api','amount':'10','currency':'CAD'};r=client.post('/commercial/invoices/1/payment-attempts',json=body);assert r.status_code==201;attempt_id=r.json()['id'];assert client.get(f'/commercial/payment-attempts/{attempt_id}').status_code==200;assert client.post('/commercial/invoices/2/payment-attempts',json={**body,'idempotency_key':'other'}).status_code==404;schema=client.get('/openapi.json').json();assert '/commercial/invoices/{invoice_id}/payment-attempts' in schema['paths'] and '/commercial/payment-attempts/{attempt_id}/reconcile' in schema['paths']
def test_authentication_failure():
 app=FastAPI();app.include_router(router);assert TestClient(app).get('/commercial/payment-attempts/1').status_code==403
