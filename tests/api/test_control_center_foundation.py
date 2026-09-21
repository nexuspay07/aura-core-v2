from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.auth.platform_admin as admin
import app.api.personal_ask_routes as ask_routes
from app.api.auth_routes import RegisterRequest
from app.db.usage_log_table import usage_log_table
from app.intelligence_v2.model_provider import MockModelProvider, ProviderUnavailableError
from tests.api.test_personal_ask_api import _client, _identity, _model_response


def _admin_client(monkeypatch, identity):
    async def current(_): return identity
    monkeypatch.setattr(admin, "get_current_user_from_token", current)
    app = FastAPI()
    @app.get("/protected")
    async def protected(user=Depends(admin.require_platform_admin)): return {"id": user["user"]["id"]}
    return TestClient(app)


def test_platform_admin_requires_auth_and_current_persisted_role(monkeypatch):
    identity = {**_identity(), "user": {"id": 1, "role": "user"}, "organization_role": "owner", "workspace_role": "admin"}
    client = _admin_client(monkeypatch, identity)
    assert client.get("/protected").status_code == 403
    assert client.get("/protected", headers={"Authorization": "Bearer jwt-claims-platform-admin"}).status_code == 403
    identity["organization_role"] = "admin"
    assert client.get("/protected", headers={"Authorization": "Bearer token"}).status_code == 403
    identity["user"]["role"] = "platform_admin"
    assert client.get("/protected", headers={"Authorization": "Bearer token"}).json() == {"id": 1}


def test_signup_contract_cannot_select_platform_admin():
    request = RegisterRequest.model_validate({"email":"user@example.com","password":"password1","role":"platform_admin"})
    assert not hasattr(request, "role")


def _events(factory):
    db=factory()
    try: return [dict(row) for row in db.execute(select(usage_log_table).order_by(usage_log_table.c.id)).mappings().all()]
    finally: db.close()


def test_success_telemetry_is_unique_typed_and_content_free(monkeypatch):
    client,factory,_,engine=_client(monkeypatch)
    prompt="PRIVATE PROMPT CREDENTIAL api-key-secret. I have two job offers. Offer A is remote. Offer B has a commute. Which should I choose?"
    try:
        response=client.post("/personal/ask",headers={"Authorization":"Bearer private-jwt"},json={"message":prompt})
        assert response.status_code==200
        rows=_events(factory);assert len(rows)==1
        row=rows[0]
        assert row["outcome"]=="success" and row["request_id"] and row["latency_ms"]>=0
        assert row["provider"]=="mock" and row["model"]=="deterministic-test"
        assert row["input_tokens"]==1 and row["output_tokens"]==1
        assert row["message"] is None and row["response"] is None
        serialized=str(row)
        for secret in (prompt,"PRIVATE_PROVIDER_OUTPUT","private-jwt","api-key-secret"):
            assert secret not in serialized
    finally: engine.dispose()


def test_clarification_safety_and_unique_request_ids(monkeypatch):
    client,factory,_,engine=_client(monkeypatch)
    try:
        headers={"Authorization":"Bearer token"}
        clarification=client.post("/personal/ask",headers=headers,json={"message":"I may leave my job."})
        safety=client.post("/personal/ask",headers=headers,json={"message":"I think I'm having a stroke."})
        assert clarification.status_code==200 and safety.status_code==200
        rows=_events(factory)
        assert [row["outcome"] for row in rows]==["clarification","safety"]
        assert len({row["request_id"] for row in rows})==2
        assert all(row["provider"] is None and row["tokens_used"] is None for row in rows)
    finally: engine.dispose()


def test_partial_and_operational_failure_are_terminal(monkeypatch):
    client,factory,_,engine=_client(monkeypatch)
    try:
        monkeypatch.setattr(ask_routes.decision_analysis_orchestrator,"provider",MockModelProvider(ProviderUnavailableError("raw private exception","rate_limit")))
        partial=client.post("/personal/ask",headers={"Authorization":"Bearer token"},json={"message":"I have two job offers. Offer A is remote. Offer B has a commute."})
        assert partial.status_code==200 and partial.json()["mode"]=="ANALYSIS_PARTIAL"
        def fail(*_,**__): raise RuntimeError("raw private exception")
        monkeypatch.setattr(ask_routes.unified_aura_orchestrator,"answer_non_decision",fail)
        failed=client.post("/personal/ask",headers={"Authorization":"Bearer token"},json={"message":"Explain compound interest."})
        assert failed.status_code==500
        rows=_events(factory)
        assert [row["outcome"] for row in rows]==["partial","failure"]
        assert rows[-1]["error_category"]=="internal_error"
        assert "raw private exception" not in str(rows)
    finally: engine.dispose()


def test_telemetry_failure_never_breaks_success(monkeypatch):
    client,_,_,engine=_client(monkeypatch)
    try:
        monkeypatch.setattr(ask_routes.telemetry_service,"record_intelligence_execution",lambda *_: (_ for _ in ()).throw(RuntimeError("down")))
        response=client.post("/personal/ask",headers={"Authorization":"Bearer token"},json={"message":"Explain compound interest."})
        assert response.status_code==200
    finally: engine.dispose()
