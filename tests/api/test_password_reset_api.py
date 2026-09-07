from datetime import datetime, timedelta, timezone
import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.auth_routes as routes
from app.core.rate_limit import FixedWindowRateLimiter
from app.core.auth_engine import auth_engine
from app.db.database import metadata
from app.db.password_reset_token_table import password_reset_token_table
from app.db.user_table import user_table


def setup(monkeypatch):
    monkeypatch.setattr(routes,"password_reset_limiter",FixedWindowRateLimiter())
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    metadata.create_all(engine); factory=sessionmaker(bind=engine); monkeypatch.setattr(routes,"SessionLocal",factory)
    db=factory(); db.execute(insert(user_table).values(id=1,email="person@example.com",password_hash=auth_engine.hash_password("old-password"),role="user",is_active=True,is_verified=True)); db.commit(); db.close()
    tokens=[]; monkeypatch.setattr(routes,"deliver_password_reset",lambda email,token: tokens.append((email,token)) or True)
    app=FastAPI();app.include_router(routes.router);return TestClient(app),factory,tokens


def test_reset_request_is_generic_and_stores_only_hash(monkeypatch):
    client,factory,tokens=setup(monkeypatch)
    existing=client.post("/auth/password-reset/request",json={"email":"person@example.com"})
    missing=client.post("/auth/password-reset/request",json={"email":"missing@example.com"})
    assert existing.status_code==missing.status_code==200
    assert existing.json()==missing.json()=={"message":routes.PASSWORD_RESET_MESSAGE}
    assert len(tokens)==1
    db=factory();stored=db.execute(select(password_reset_token_table)).mappings().one();db.close()
    assert stored["token_hash"]!=tokens[0][1] and tokens[0][1] not in str(stored)


def test_reset_token_is_one_time_and_changes_password(monkeypatch):
    client,_,tokens=setup(monkeypatch);client.post("/auth/password-reset/request",json={"email":"person@example.com"});token=tokens[0][1]
    assert client.post("/auth/password-reset/confirm",json={"token":token,"password":"new-password"}).status_code==200
    assert client.post("/auth/password-reset/confirm",json={"token":token,"password":"another-password"}).status_code==400
    assert client.post("/auth/login",json={"email":"person@example.com","password":"old-password"}).status_code==401
    assert client.post("/auth/login",json={"email":"person@example.com","password":"new-password"}).status_code==200


def test_expired_and_invalid_tokens_are_rejected(monkeypatch):
    client,factory,_=setup(monkeypatch);expired="x"*48;db=factory();db.execute(insert(password_reset_token_table).values(user_id=1,token_hash=hashlib.sha256(expired.encode()).hexdigest(),created_at=datetime.now(timezone.utc)-timedelta(hours=2),expires_at=datetime.now(timezone.utc)-timedelta(hours=1)));db.commit();db.close()
    assert client.post("/auth/password-reset/confirm",json={"token":expired,"password":"new-password"}).status_code==400
    assert client.post("/auth/password-reset/confirm",json={"token":"invalid"*8,"password":"new-password"}).status_code==400

def test_new_request_invalidates_earlier_unused_token(monkeypatch):
    client,_,tokens=setup(monkeypatch)
    client.post("/auth/password-reset/request",json={"email":"person@example.com"});first=tokens[-1][1]
    client.post("/auth/password-reset/request",json={"email":"person@example.com"});second=tokens[-1][1]
    assert client.post("/auth/password-reset/confirm",json={"token":first,"password":"new-password"}).status_code==400
    assert client.post("/auth/password-reset/confirm",json={"token":second,"password":"new-password"}).status_code==200

def test_provider_failure_keeps_generic_response(monkeypatch):
    client,_,_=setup(monkeypatch);monkeypatch.setattr(routes,"deliver_password_reset",lambda *_:False)
    response=client.post("/auth/password-reset/request",json={"email":"person@example.com"})
    assert response.status_code==200 and response.json()=={"message":routes.PASSWORD_RESET_MESSAGE}
