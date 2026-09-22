"""Control Center authorization, aggregate correctness, and privacy gates."""
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.control_center_routes as routes
import app.auth.platform_admin as admin
from app.db.database import metadata
from app.db.intelligence_session_table import intelligence_session_table  # noqa: F401
from app.db.organization_member_table import organization_member_table
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.usage_log_table import usage_log_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table


def _setup(monkeypatch, *, populated=True):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(routes, "SessionLocal", factory)
    identity = {"user": {"id": 99, "role": "platform_admin"}, "organization_role": "member", "workspace_role": "member"}
    async def current(_): return identity
    monkeypatch.setattr(admin, "get_current_user_from_token", current)
    now = datetime.now(timezone.utc)
    if populated:
        with factory.begin() as db:
            db.execute(insert(user_table), [
                {"id": 1, "email": "old@example.test", "password_hash": "PRIVATE_HASH", "full_name": "Old User", "created_at": now-timedelta(days=40), "is_active": True, "is_verified": True},
                {"id": 2, "email": "new@example.test", "password_hash": "PRIVATE_HASH_2", "full_name": "New User", "created_at": now-timedelta(days=1), "is_active": True, "is_verified": False},
                {"id": 99, "email": "admin@example.test", "password_hash": "ADMIN_PRIVATE", "full_name": None, "role": "platform_admin", "created_at": now-timedelta(days=60), "is_active": True, "is_verified": True},
            ])
            db.execute(insert(organization_table), {"id": 1, "name": "Org", "slug": "control-org", "owner_user_id": 1, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True})
            db.execute(insert(workspace_table), {"id": 1, "organization_id": 1, "created_by_user_id": 1, "name": "Workspace", "slug": "control-workspace", "workspace_type": "personal", "is_active": True})
            db.execute(insert(organization_member_table), [{"organization_id": 1, "user_id": 1, "role": "owner", "is_active": True}, {"organization_id": 1, "user_id": 2, "role": "member", "is_active": True}])
            db.execute(insert(workspace_member_table), [{"workspace_id": 1, "user_id": 1, "role": "admin", "is_active": True}, {"workspace_id": 1, "user_id": 2, "role": "member", "is_active": True}])
            base = {"organization_id": 1, "workspace_id": 1, "route": "/personal/ask", "message": None, "response": None, "success": True,
                    "request_mode": None, "provider": None, "model": None, "input_tokens": None, "output_tokens": None,
                    "reasoning_tokens": None, "tokens_used": None, "latency_ms": None, "retry_count": None,
                    "provider_call_count": None, "error_category": None}
            db.execute(insert(usage_log_table), [
                {**base, "request_id": "prior", "user_id": 1, "outcome": "success", "request_mode": "ANALYSIS_COMPLETE", "latency_ms": 50, "created_at": now-timedelta(days=10)},
                {**base, "request_id": "success", "user_id": 1, "outcome": "success", "request_mode": "ANALYSIS_COMPLETE", "provider": "mock", "model": "model-a", "input_tokens": 3, "output_tokens": 4, "reasoning_tokens": 1, "tokens_used": 8, "latency_ms": 100, "retry_count": 1, "provider_call_count": 2, "created_at": now-timedelta(hours=2)},
                {**base, "request_id": "failure", "user_id": 2, "outcome": "failure", "error_category": "timeout", "success": False, "latency_ms": 300, "created_at": now-timedelta(hours=1)},
                {**base, "request_id": "clarify", "user_id": 2, "outcome": "clarification", "request_mode": "CLARIFICATION_REQUIRED", "latency_ms": 200, "created_at": now-timedelta(minutes=30)},
            ])
            db.execute(insert(personal_decision_table), {"id": 1, "user_id": 1, "organization_id": 1, "workspace_id": 1, "title": "PRIVATE TITLE", "original_question": "PRIVATE QUESTION", "decision_type": "choice", "analysis_snapshot_json": {"private": "content"}, "recommendation": "PRIVATE RECOMMENDATION", "created_at": now-timedelta(hours=3)})
    app = FastAPI(); app.include_router(routes.router)
    return TestClient(app), identity, engine


def test_every_endpoint_uses_persisted_platform_admin_gate(monkeypatch):
    client, identity, engine = _setup(monkeypatch)
    try:
        endpoints = ("overview", "users", "intelligence")
        for endpoint in endpoints:
            assert client.get(f"/admin/control-center/{endpoint}").status_code == 403
        identity["user"]["role"] = "user"
        identity["organization_role"] = "owner"
        identity["workspace_role"] = "admin"
        for endpoint in endpoints:
            assert client.get(f"/admin/control-center/{endpoint}", headers={"Authorization": "Bearer stale-platform_admin"}).status_code == 403
        identity["organization_role"] = "admin"
        for endpoint in endpoints:
            assert client.get(f"/admin/control-center/{endpoint}", headers={"Authorization": "Bearer token"}).status_code == 403
        identity["user"]["role"] = "platform_admin"
        for endpoint in endpoints:
            assert client.get(f"/admin/control-center/{endpoint}", headers={"Authorization": "Bearer token"}).status_code == 200
    finally: engine.dispose()


def test_overview_metrics_definitions_boundaries_and_privacy(monkeypatch):
    client, _, engine = _setup(monkeypatch)
    try:
        body = client.get("/admin/control-center/overview?window=7d", headers={"Authorization":"Bearer token"}).json()
        assert body["users"] == {"total_users":3, "new_users_in_window":1, "active_users_in_window":2, "returning_users_in_window":1}
        assert body["intelligence"]["total_requests"] == 3
        assert body["intelligence"]["successful_requests"] == 1 and body["intelligence"]["failed_requests"] == 1
        assert body["intelligence"]["clarification_requests"] == 1
        assert body["intelligence"]["operational_reliability_rate"] == .5
        assert body["decisions"] == {"total_saved_decisions":1, "new_saved_decisions_in_window":1}
        assert body["performance"] == {"average_latency_ms":200.0, "p50_latency_ms":200, "p95_latency_ms":300}
        assert body["usage"]["known_total_tokens"] == 8 and body["usage"]["requests_with_token_data"] == 1
        assert body["data_completeness"]["request_telemetry"].startswith("partial")
        serialized = str(body)
        for private in ("PRIVATE_HASH", "PRIVATE QUESTION", "PRIVATE RECOMMENDATION", "analysis_snapshot"):
            assert private not in serialized
    finally: engine.dispose()


def test_users_stable_cursor_pagination_counts_and_safe_dto(monkeypatch):
    client, _, engine = _setup(monkeypatch)
    try:
        headers={"Authorization":"Bearer token"}
        first=client.get("/admin/control-center/users?window=7d&page_size=1",headers=headers).json()
        second=client.get(f"/admin/control-center/users?window=7d&page_size=1&cursor={first['next_cursor']}",headers=headers).json()
        assert first["items"][0]["user_id"] != second["items"][0]["user_id"]
        all_users=client.get("/admin/control-center/users?window=7d&page_size=100",headers=headers).json()["items"]
        old=next(item for item in all_users if item["user_id"]==1)
        assert old["organization_count"]==1 and old["workspace_count"]==1
        assert old["request_count_in_window"]==1 and old["saved_decision_count"]==1 and old["last_intelligence_activity"]
        assert client.get("/admin/control-center/users?page_size=101",headers=headers).status_code==422
        assert client.get("/admin/control-center/users?cursor=bad",headers=headers).status_code==422
        assert "password" not in str(all_users).lower() and "PRIVATE" not in str(all_users)
    finally: engine.dispose()


def test_intelligence_aggregates_coverage_series_and_privacy(monkeypatch):
    client, _, engine = _setup(monkeypatch)
    try:
        body=client.get("/admin/control-center/intelligence?window=24h",headers={"Authorization":"Bearer token"}).json()
        assert body["total_requests"]==3 and body["bucket"]=="hour"
        assert {x["key"]:x["count"] for x in body["outcomes"]}=={"clarification":1,"failure":1,"success":1}
        assert body["provider_coverage"]=={"known_provider_requests":1,"unknown_provider_requests":2,"known_model_requests":1,"unknown_model_requests":2}
        assert body["tokens"]["requests_with_token_data"]==1 and body["tokens"]["requests_without_token_data"]==2
        assert body["execution"]=={"total_retries":1,"requests_with_retries":1,"known_provider_calls":2,"requests_with_provider_call_data":1}
        assert sum(point["request_count"] for point in body["time_series"])==3
        assert "PRIVATE" not in str(body) and "message" not in body and "response" not in body
    finally: engine.dispose()


def test_empty_data_and_window_validation(monkeypatch):
    client, _, engine = _setup(monkeypatch, populated=False)
    try:
        headers={"Authorization":"Bearer token"}
        overview=client.get("/admin/control-center/overview",headers=headers).json()
        assert overview["intelligence"]["total_requests"]==0
        assert overview["intelligence"]["operational_reliability_rate"] is None
        assert overview["performance"]["average_latency_ms"] is None
        assert client.get("/admin/control-center/intelligence?window=all",headers=headers).status_code==422
    finally: engine.dispose()
