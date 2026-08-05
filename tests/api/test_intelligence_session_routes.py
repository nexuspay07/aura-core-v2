from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.intelligence_session_routes as routes
from app.db.database import metadata
from app.db.intelligence_session_table import intelligence_session_table
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table


def _identity(organization_id=1):
    return {"user":{"id":1},"organization":{"id":organization_id},"workspace":{"id":1}}


def _client(monkeypatch):
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    event.listen(engine,"connect",lambda connection,_:connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    db=factory()
    db.execute(insert(user_table),[{"id":1,"email":"one@test","password_hash":"x"},{"id":2,"email":"two@test","password_hash":"x"}])
    db.execute(insert(organization_table),[{"id":1,"name":"One","slug":"one","owner_user_id":1,"plan":"free","subscription_status":"inactive","is_active":True},{"id":2,"name":"Two","slug":"two","owner_user_id":2,"plan":"free","subscription_status":"inactive","is_active":True}])
    db.execute(insert(workspace_table),[{"id":1,"organization_id":1,"created_by_user_id":1,"name":"One","slug":"one-space","workspace_type":"business","is_active":True},{"id":2,"organization_id":2,"created_by_user_id":2,"name":"Two","slug":"two-space","workspace_type":"business","is_active":True}])
    db.execute(insert(workspace_member_table),[{"workspace_id":1,"user_id":1,"role":"admin","status":"active","is_active":True},{"workspace_id":2,"user_id":2,"role":"admin","status":"active","is_active":True}])
    db.commit();db.close()
    async def current(_): return _identity()
    monkeypatch.setattr(routes,"SessionLocal",factory);monkeypatch.setattr(routes,"get_current_user_from_token",current)
    app=FastAPI();app.include_router(routes.router)
    return TestClient(app),factory


def test_owned_workspace_empty_and_cross_organization_hidden(monkeypatch):
    client,_=_client(monkeypatch)
    response=client.get("/intelligence-sessions/workspace/1",headers={"Authorization":"Bearer test"})
    assert response.status_code==200 and response.json()["sessions"]==[]
    assert client.get("/intelligence-sessions/workspace/2",headers={"Authorization":"Bearer test"}).status_code==404


def test_missing_or_invalid_credentials_are_rejected(monkeypatch):
    client,_=_client(monkeypatch)
    assert client.get("/intelligence-sessions/workspace/1").status_code==403

    async def invalid(_):
        raise HTTPException(status_code=401,detail="Invalid token")
    monkeypatch.setattr(routes,"get_current_user_from_token",invalid)
    assert client.get("/intelligence-sessions/workspace/1",headers={"Authorization":"Bearer invalid"}).status_code==401


def test_list_retrieve_create_and_delete_use_nested_identity(monkeypatch):
    client,factory=_client(monkeypatch)
    db=factory();db.execute(insert(intelligence_session_table).values(id=1,organization_id=1,workspace_id=1,created_by_user_id=1,title="Existing",goal="Goal",domain="business",session_type="decision_analysis",status="completed",is_active=True));db.commit();db.close()
    assert client.get("/intelligence-sessions/workspace/1",headers={"Authorization":"Bearer test"}).json()["sessions"][0]["id"]==1
    assert client.get("/intelligence-sessions/1",headers={"Authorization":"Bearer test"}).status_code==200
    assert client.get("/intelligence-sessions/1",headers={"Authorization":"Bearer test"}).status_code==200
    assert client.delete("/intelligence-sessions/1",headers={"Authorization":"Bearer test"}).status_code==200


def test_create_ignores_client_organization_and_preserves_workspace_scope(monkeypatch):
    client,_=_client(monkeypatch)
    async def intelligence(_): return "summary"
    monkeypatch.setattr(routes,"generate_strategic_intelligence",intelligence)
    response=client.post("/intelligence-sessions",headers={"Authorization":"Bearer test"},json={"organization_id":2,"workspace_id":1,"title":"New","goal":"Goal"})
    assert response.status_code==200 and response.json()["session"]["organization_id"]==1


def test_cross_organization_create_retrieve_and_delete_are_hidden(monkeypatch):
    client,factory=_client(monkeypatch)
    db=factory()
    db.execute(insert(intelligence_session_table).values(id=1,organization_id=1,workspace_id=1,created_by_user_id=1,title="Existing",goal="Goal",domain="business",session_type="decision_analysis",status="completed",is_active=True))
    db.commit();db.close()

    async def other_organization(_): return _identity(2)
    monkeypatch.setattr(routes,"get_current_user_from_token",other_organization)

    assert client.get("/intelligence-sessions/1",headers={"Authorization":"Bearer test"}).status_code==404
    assert client.delete("/intelligence-sessions/1",headers={"Authorization":"Bearer test"}).status_code==404
    response=client.post("/intelligence-sessions",headers={"Authorization":"Bearer test"},json={"workspace_id":1,"title":"New","goal":"Goal"})
    assert response.status_code==404
    db=factory()
    assert db.execute(intelligence_session_table.select()).mappings().all()[0]["is_active"] is True
    db.close()
