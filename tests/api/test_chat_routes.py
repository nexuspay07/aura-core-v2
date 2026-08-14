"""Decision Center chat persistence and tenant-bound session regressions."""

from datetime import datetime, timezone
import inspect

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.chat_routes as routes
import app.core.cognitive_loop_v2 as cognitive_loop_module
import app.services.chat_service as chat_module
from app.db.database import metadata
from app.db.intelligence_session_table import intelligence_session_table
from app.db.memory_table import memory_table
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.services.session_service import session_service


def _identity(organization_id=1, workspace_id=1, user_id=1):
    return {
        "user": {"id": user_id, "email": f"user-{user_id}@test"},
        "organization": {"id": organization_id, "name": f"Organization {organization_id}"},
        "workspace": {"id": workspace_id, "name": f"Workspace {workspace_id}"},
    }


def _client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.execute(insert(user_table), [{"id": 1, "email": "one@test", "password_hash": "x"}, {"id": 2, "email": "two@test", "password_hash": "x"}])
    db.execute(insert(organization_table), [{"id": 1, "name": "One", "slug": "one", "owner_user_id": 1}, {"id": 2, "name": "Two", "slug": "two", "owner_user_id": 2}])
    db.execute(insert(workspace_table), [{"id": 1, "organization_id": 1, "created_by_user_id": 1, "name": "One", "slug": "one-space"}, {"id": 2, "organization_id": 2, "created_by_user_id": 2, "name": "Two", "slug": "two-space"}])
    db.commit()
    db.close()

    async def current(_):
        return _identity()

    async def build_context(**_):
        return {"business": {"organization_name": "One", "workspace_name": "One", "captured_at": datetime(2026, 8, 8, tzinfo=timezone.utc)}}

    async def run(request):
        return request

    def response(*, request, session_id):
        return {
            "success": True,
            "session_id": session_id,
            "executive_report": {
                "executive_summary": "Structured report",
                "confidence": {"score": 80},
                "implementation_roadmap": [],
                "generated_at": datetime(2026, 8, 8, tzinfo=timezone.utc),
            },
            "nested": {"captured_at": datetime(2026, 8, 8, tzinfo=timezone.utc)},
        }

    monkeypatch.setattr(routes, "get_current_user_from_token", current)
    monkeypatch.setattr(chat_module, "SessionLocal", factory)
    monkeypatch.setattr(chat_module.aura_context_service, "build", build_context)
    monkeypatch.setattr(chat_module.cognitive_loop, "run", run)
    monkeypatch.setattr(chat_module.response_service, "build_response", response)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app, raise_server_exceptions=False), factory


def test_chat_creates_json_safe_tenant_scoped_session_and_returns_executive_report(monkeypatch):
    client, factory = _client(monkeypatch)
    response = client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Reduce delivery cost"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["executive_report"]["executive_summary"] == "Structured report"
    assert isinstance(payload["session_id"], int)

    db = factory()
    record = db.execute(select(intelligence_session_table)).mappings().one()
    assert (record["organization_id"], record["workspace_id"], record["created_by_user_id"]) == (1, 1, 1)
    assert record["report_json"]["nested"]["captured_at"] == "2026-08-08T00:00:00+00:00"
    assert db.execute(select(func.count()).select_from(memory_table)).scalar_one() == 1
    db.close()


def test_chat_reuses_owned_session_and_hides_cross_tenant_or_missing_sessions(monkeypatch):
    client, factory = _client(monkeypatch)
    first = client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "First"}).json()
    second = client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Second", "session_id": first["session_id"]})
    assert second.status_code == 200 and second.json()["session_id"] == first["session_id"]
    db = factory()
    assert db.execute(select(func.count()).select_from(intelligence_session_table)).scalar_one() == 1
    db.close()

    async def other_tenant(_):
        return _identity(organization_id=2, workspace_id=2, user_id=2)

    monkeypatch.setattr(routes, "get_current_user_from_token", other_tenant)
    assert client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Cross tenant", "session_id": first["session_id"]}).status_code == 404
    assert client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Missing", "session_id": 999}).status_code == 404


def test_chat_rejects_spoofed_tenant_context_and_requires_authentication(monkeypatch):
    client, _ = _client(monkeypatch)
    assert client.post("/chat", json={"message": "No auth"}).status_code == 403
    assert client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Spoof", "organization_id": 2}).status_code == 403
    assert client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Spoof", "workspace_id": 2}).status_code == 403


def test_session_failure_rolls_back_the_related_memory_write(monkeypatch):
    client, factory = _client(monkeypatch)

    def fail_create(**_):
        raise RuntimeError("session persistence failed")

    monkeypatch.setattr(session_service, "create_session", fail_create)
    response = client.post("/chat", headers={"Authorization": "Bearer token"}, json={"message": "Atomic request"})
    assert response.status_code == 500
    db = factory()
    assert db.execute(select(func.count()).select_from(memory_table)).scalar_one() == 0
    assert db.execute(select(func.count()).select_from(intelligence_session_table)).scalar_one() == 0
    db.close()


def test_cognitive_loop_does_not_dump_full_request_context():
    source = inspect.getsource(cognitive_loop_module.CognitiveLoop.run)
    assert "print(request)" not in source
    assert "logger.debug" in source
