from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.personal_decision_routes as routes
from app.db.database import metadata
from app.db.intelligence_session_table import intelligence_session_table
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table


def _identity(*, user_id=1, organization_id=1, workspace_id=1, capabilities=None):
    return {"user": {"id": user_id}, "organization": {"id": organization_id}, "workspace": {"id": workspace_id}, "capabilities": capabilities if capabilities is not None else ["decisions"]}


def _client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.execute(insert(user_table), [{"id": 1, "email": "one@test", "password_hash": "x"}, {"id": 2, "email": "two@test", "password_hash": "x"}])
    db.execute(insert(organization_table), [{"id": 1, "name": "One", "slug": "one-personal", "owner_user_id": 1, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True}, {"id": 2, "name": "Two", "slug": "two-personal", "owner_user_id": 2, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True}])
    db.execute(insert(workspace_table), [{"id": 1, "organization_id": 1, "created_by_user_id": 1, "name": "One", "slug": "one-workspace", "workspace_type": "personal", "is_active": True}, {"id": 2, "organization_id": 2, "created_by_user_id": 2, "name": "Two", "slug": "two-workspace", "workspace_type": "personal", "is_active": True}, {"id": 3, "organization_id": 1, "created_by_user_id": 1, "name": "Three", "slug": "three-workspace", "workspace_type": "personal", "is_active": True}])
    db.execute(insert(intelligence_session_table), [{"id": 1, "organization_id": 1, "workspace_id": 1, "created_by_user_id": 1, "title": "Career", "goal": "Which offer?", "session_type": "decision_analysis", "status": "completed", "is_active": True, "report_json": {"executive_report": {"executive_summary": "Compare offers", "recommended_move": "Verify growth"}}}, {"id": 2, "organization_id": 2, "workspace_id": 2, "created_by_user_id": 2, "title": "Other", "goal": "Other", "session_type": "decision_analysis", "status": "completed", "is_active": True, "report_json": None}])
    db.commit(); db.close()
    active = {"identity": _identity()}
    async def current(_): return active["identity"]
    monkeypatch.setattr(routes, "SessionLocal", factory)
    monkeypatch.setattr(routes, "get_current_user_from_token", current)
    app = FastAPI(); app.include_router(routes.router)
    return TestClient(app), factory, active, engine


def test_personal_create_list_get_update_and_delete(monkeypatch):
    client, factory, _, engine = _client(monkeypatch)
    try:
        created = client.post("/personal/decisions", headers={"Authorization": "Bearer token"}, json={"source_session_id": 1, "title": "Career choice", "decision_type": "career_decision", "organization_id": 2, "workspace_id": 2, "user_id": 2})
        assert created.status_code == 201, created.text
        decision = created.json()
        duplicate = client.post("/personal/decisions", headers={"Authorization": "Bearer token"}, json={"source_session_id": 1})
        assert duplicate.status_code == 409
        assert (decision["user_id"], decision["organization_id"], decision["workspace_id"]) == (1, 1, 1)
        assert "provider_request" not in decision["analysis_snapshot"]
        assert client.get("/personal/decisions?status=open&decision_type=career_decision", headers={"Authorization": "Bearer token"}).json()[0]["id"] == decision["id"]
        updated = client.patch(f"/personal/decisions/{decision['id']}", headers={"Authorization": "Bearer token"}, json={"user_choice": "Offer A", "user_choice_rationale": "Time", "review_date": "2026-09-01T00:00:00Z"})
        assert updated.status_code == 200 and updated.json()["status"] == "decided" and updated.json()["recommendation"] == "Verify growth"
        assert client.delete(f"/personal/decisions/{decision['id']}", headers={"Authorization": "Bearer token"}).status_code == 204
        db = factory(); assert db.execute(select(personal_decision_table)).mappings().all() == []; assert db.execute(select(intelligence_session_table).where(intelligence_session_table.c.id == 1)).mappings().one(); db.close()
    finally:
        engine.dispose()


def test_capability_and_cross_tenant_sources_and_records_are_hidden(monkeypatch):
    client, factory, active, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer token"}
        assert client.post("/personal/decisions", headers=headers, json={"source_session_id": 2}).status_code == 404
        created = client.post("/personal/decisions", headers=headers, json={"source_session_id": 1}).json()
        active["identity"] = _identity(user_id=2, organization_id=2, workspace_id=2)
        assert client.get(f"/personal/decisions/{created['id']}", headers=headers).status_code == 404
        assert client.delete(f"/personal/decisions/{created['id']}", headers=headers).status_code == 404
        active["identity"] = _identity(capabilities=[])
        assert client.get("/personal/decisions", headers=headers).status_code == 404
    finally:
        engine.dispose()
