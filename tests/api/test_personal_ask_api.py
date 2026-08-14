"""Offline integration coverage for the authenticated Personal Ask V2 contract."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.personal_ask_routes as routes
import app.api.personal_decision_routes as decision_routes
from app.db.database import metadata
from app.db.intelligence_session_table import intelligence_session_table
from app.db.organization_member_table import organization_member_table
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.intelligence_v2.model_provider import MockModelProvider, ProviderTimeoutError, ProviderUnavailableError
from app.unified_intelligence.contracts import ModelResult
from app.db.memory_table import memory_table


class _GeneralProvider:
    provider_name = "offline"; model_name = "general-test"; capabilities = {"natural_text_generation"}
    def __init__(self): self.requests = []
    def generate(self, request):
        self.requests.append(request)
        return ModelResult("A useful Aura answer.", {"provider":"offline","model":"general-test","input_tokens":5,"output_tokens":6,"total_tokens":11})


def _identity(*, user_id=1, organization_id=1, workspace_id=1, capabilities=None):
    return {
        "user": {"id": user_id}, "organization": {"id": organization_id},
        "workspace": {"id": workspace_id},
        "capabilities": ["ask_aura", "decisions"] if capabilities is None else capabilities,
    }


def _model_response():
    return {
        "problem_summary": "Compare the supplied options.",
        "alternatives": [{"option": "Offer A", "benefits": ["Remote work"], "downsides": ["Limited promotion"], "evidence_ids": ["user-query"], "assumptions": [], "conditions_for_success": ["Confirm growth options"]}],
        "recommended_option": "Offer A", "rationale": "The supplied trade-off requires a conditional choice.",
        "key_tradeoffs": ["Growth versus evenings"], "risks": [], "assumptions_used": [],
        "evidence_ids": ["user-query"], "unresolved_questions": [], "recommendation_change_conditions": ["The recommendation changes if the growth path is materially stronger elsewhere."],
    }


def _client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.execute(insert(user_table), [{"id": 1, "email": "one@example.test", "password_hash": "x"}, {"id": 2, "email": "two@example.test", "password_hash": "x"}])
    db.execute(insert(organization_table), [
        {"id": 1, "name": "One", "slug": "one-ask", "owner_user_id": 1, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 2, "name": "Two", "slug": "two-ask", "owner_user_id": 2, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    db.execute(insert(workspace_table), [
        {"id": 1, "organization_id": 1, "created_by_user_id": 1, "name": "One", "slug": "one-ask-workspace", "workspace_type": "personal", "is_active": True},
        {"id": 2, "organization_id": 2, "created_by_user_id": 2, "name": "Two", "slug": "two-ask-workspace", "workspace_type": "personal", "is_active": True},
    ])
    db.execute(insert(organization_member_table), [
        {"organization_id": 1, "user_id": 1, "role": "owner", "is_active": True},
        {"organization_id": 2, "user_id": 2, "role": "owner", "is_active": True},
    ])
    db.execute(insert(workspace_member_table), [
        {"workspace_id": 1, "user_id": 1, "role": "admin", "is_active": True},
        {"workspace_id": 2, "user_id": 2, "role": "admin", "is_active": True},
    ])
    db.commit(); db.close()
    active = {"identity": _identity()}
    async def current(_): return active["identity"]
    monkeypatch.setattr(routes, "SessionLocal", factory)
    monkeypatch.setattr(routes, "get_current_user_from_token", current)
    monkeypatch.setattr(decision_routes, "SessionLocal", factory)
    monkeypatch.setattr(decision_routes, "get_current_user_from_token", current)
    monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", MockModelProvider(_model_response()))
    app = FastAPI(); app.include_router(routes.router); app.include_router(decision_routes.router)
    return TestClient(app, raise_server_exceptions=False), factory, active, engine


def test_personal_ask_auth_capability_complete_and_save_decision(monkeypatch):
    client, factory, active, engine = _client(monkeypatch)
    try:
        assert client.post("/personal/ask", json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."}).status_code == 403
        active["identity"] = _identity(capabilities=[])
        assert client.post("/personal/ask", headers={"Authorization": "Bearer test"}, json={"message": "Question"}).status_code == 404
        active["identity"] = _identity()
        response = client.post("/personal/ask", headers={"Authorization": "Bearer test"}, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["mode"] == "ANALYSIS_COMPLETE" and result["classification"] == "career_decision"
        assert "provider" not in result and "raw" not in result
        db = factory(); session = db.execute(select(intelligence_session_table).where(intelligence_session_table.c.id == result["session_id"])).mappings().one()
        assert (session["created_by_user_id"], session["organization_id"], session["workspace_id"]) == (1, 1, 1)
        assert session["session_type"] == "personal_ask_v2" and session["report_json"]["executive_report"]["recommendation"]
        saved = client.post("/personal/decisions", headers={"Authorization": "Bearer test"}, json={"source_session_id": result["session_id"], "decision_type": "career_decision"})
        assert saved.status_code == 201, saved.text
        assert db.execute(select(personal_decision_table)).mappings().one()["source_session_id"] == result["session_id"]
        db.close()
    finally:
        engine.dispose()


def test_clarification_continues_owned_session_without_context_promotion(monkeypatch):
    client, factory, _, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        first = client.post("/personal/ask", headers=headers, json={"message": "I may leave my current job."})
        assert first.status_code == 200 and first.json()["mode"] == "CLARIFICATION_REQUIRED"
        second = client.post("/personal/ask", headers=headers, json={"session_id": first.json()["session_id"], "clarification_response": "I want to move into product management."})
        assert second.status_code == 200 and second.json()["mode"] == "CLARIFICATION_REQUIRED", second.text
        third = client.post("/personal/ask", headers=headers, json={"session_id": first.json()["session_id"], "clarification_response": "I have twelve months of financial runway."})
        assert third.status_code == 200 and third.json()["mode"] == "ANALYSIS_COMPLETE"
        db = factory(); report = db.execute(select(intelligence_session_table.c.report_json).where(intelligence_session_table.c.id == first.json()["session_id"])).scalar_one()
        assert len(report["personal_ask"]["clarification_answers"]) == 2
        # Ask answers stay in the session artifact; this route does not create
        # Personal Context records automatically.
        assert "personal_context" not in report
        db.close()
    finally:
        engine.dispose()


def test_personal_ask_session_isolation_and_safe_failures_rollback(monkeypatch, caplog):
    client, factory, active, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        created = client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."}).json()
        active["identity"] = _identity(user_id=2, organization_id=2, workspace_id=2)
        assert client.post("/personal/ask", headers=headers, json={"session_id": created["session_id"], "message": "Continue"}).status_code == 404
        active["identity"] = _identity()
        monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", MockModelProvider(ProviderUnavailableError("secret should not leak", "rate_limit")))
        failed = client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."})
        assert failed.status_code == 503 and "secret" not in failed.text and "rate_limit" not in failed.text
        diagnostic = next(record.message for record in caplog.records if "personal_ask_provider_failure" in record.message)
        assert '"error_category": "rate_limit"' in diagnostic and '"product_route": "/personal/ask"' in diagnostic
        assert "secret" not in diagnostic and "two job offers" not in diagnostic
        db = factory(); assert db.execute(select(intelligence_session_table)).mappings().all().__len__() == 1; db.close()
        monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", MockModelProvider(ProviderTimeoutError("timeout", "timeout")))
        assert client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."}).status_code == 504
    finally:
        engine.dispose()


def test_provider_categories_and_timeout_remain_sanitized_without_real_calls(monkeypatch, caplog):
    client, _, _, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        for category in ("authentication_error", "rate_limit", "bad_request", "api_connection_error", "unknown_provider_error"):
            provider = MockModelProvider(ProviderUnavailableError("key=not-for-log prompt=private", category, {"provider": "openai", "model": "gpt-5.1", "exception_type": "FakeProviderError", "http_status": 400, "raw": "private evidence"}))
            monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", provider)
            response = client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."})
            assert response.status_code == 503 and response.json()["detail"] == "Aura is temporarily unavailable. Please try again later."
            assert provider.calls == 1
        timeout_provider = MockModelProvider(ProviderTimeoutError("private", "timeout", {"provider": "openai", "model": "gpt-5.1", "error_category": "timeout", "latency_ms": 90}))
        monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", timeout_provider)
        assert client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."}).status_code == 504
        messages = "\n".join(record.message for record in caplog.records)
        for category in ("authentication_error", "rate_limit", "bad_request", "api_connection_error", "unknown_provider_error"):
            assert f'"error_category": "{category}"' in messages
        assert '"error_category": "timeout"' in messages
        assert "not-for-log" not in messages and "private decision prompt" not in messages and "private evidence" not in messages
    finally:
        engine.dispose()


def test_spoofed_scope_is_rejected_and_grounding_failure_is_not_persisted(monkeypatch):
    client, factory, active, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        spoofed = client.post("/personal/ask", headers=headers, json={
            "message": "I have two job offers. Offer A is remote. Offer B has a commute.",
            "user_id": 2, "organization_id": 2, "workspace_id": 2,
        })
        assert spoofed.status_code == 422
        bad = _model_response(); bad["evidence_ids"] = ["invented-evidence"]
        monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", MockModelProvider(bad))
        rejected = client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."})
        assert rejected.status_code == 422 and "invented-evidence" not in rejected.text
        db = factory(); assert db.execute(select(intelligence_session_table)).mappings().all() == []; db.close()
        # Ask Aura remains available to the existing Business product mode;
        # tenant capability policy, not a route-local account type check, gates it.
        active["identity"] = _identity(capabilities=["ask_aura"])
        monkeypatch.setattr(routes.decision_analysis_orchestrator, "provider", MockModelProvider(_model_response()))
        assert client.post("/personal/ask", headers=headers, json={"message": "I have two job offers. Offer A is remote. Offer B has a commute."}).status_code == 200
    finally:
        engine.dispose()


def test_personal_ask_openapi_and_legacy_chat_contract_remain_distinct(monkeypatch):
    client, _, _, engine = _client(monkeypatch)
    try:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/personal/ask" in paths and "/chat" not in paths
        assert "PersonalAskRequest" in client.get("/openapi.json").json()["components"]["schemas"]
    finally:
        engine.dispose()


def test_conversation_mode_is_truthful_persisted_and_does_not_create_decision(monkeypatch):
    client, factory, _, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        response = client.post("/personal/ask", headers=headers, json={"message": "Hello"})
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "CONVERSATION" and body["session_id"]
        db = factory()
        assert db.execute(select(personal_decision_table)).mappings().all() == []
        stored = db.execute(select(intelligence_session_table).where(intelligence_session_table.c.id == body["session_id"])).mappings().one()
        assert stored["domain"] == "personal" and stored["report_json"]["conversation"]["response"] == body["message"]
        assert [turn["role"] for turn in stored["report_json"]["turns"]] == ["user", "assistant"]
        assert "chain_of_thought" not in str(stored["report_json"]).lower()
        db.close()
    finally:
        engine.dispose()


def test_exact_car_scenario_is_major_purchase_without_delivery_questions(monkeypatch):
    client, _, _, engine = _client(monkeypatch)
    try:
        message = "I have $32,000 in savings and I'm thinking about buying a car for $18,000 in cash. I earn $4,200 per month and my regular monthly expenses are about $2,600. I want to keep at least $20,000 in emergency savings because financial security is important to me, but I also need a reliable car. Should I buy the $18,000 car now, choose a cheaper car, or wait and save more?"
        response = client.post("/personal/ask", headers={"Authorization": "Bearer test"}, json={"message": message})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["classification"] == "major_purchase"
        assert body["mode"] == "ANALYSIS_COMPLETE"
        assert not any(term in " ".join(body.get("questions", [])).lower() for term in ("delivery", "fleet", "carrier", "order"))
    finally:
        engine.dispose()


def test_owned_conversation_recovery_restores_turns_and_hides_cross_tenant(monkeypatch):
    client, factory, active, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        created = client.post("/personal/ask", headers=headers, json={"message": "Hello"}).json()
        recovered = client.get(f"/personal/ask/{created['session_id']}", headers=headers)
        assert recovered.status_code == 200
        assert [turn["role"] for turn in recovered.json()["turns"]] == ["user", "assistant"]
        active["identity"] = _identity(user_id=2, organization_id=2, workspace_id=2)
        assert client.get(f"/personal/ask/{created['session_id']}", headers=headers).status_code == 404
        db = factory(); assert db.execute(select(personal_decision_table)).mappings().all() == []; db.close()
    finally:
        engine.dispose()


def test_clarification_and_completed_decision_survive_recovery(monkeypatch):
    client, _, _, engine = _client(monkeypatch)
    try:
        headers = {"Authorization": "Bearer test"}
        first = client.post("/personal/ask", headers=headers, json={"message": "I may leave my current job."}).json()
        restored = client.get(f"/personal/ask/{first['session_id']}", headers=headers).json()
        assert restored["pending_clarification"] is True
        assert restored["turns"][-1]["mode"] == "CLARIFICATION_REQUIRED"
        client.post("/personal/ask", headers=headers, json={"session_id": first["session_id"], "clarification_response": "I want product leadership."})
        complete = client.post("/personal/ask", headers=headers, json={"session_id": first["session_id"], "clarification_response": "I have twelve months of runway."}).json()
        restored = client.get(f"/personal/ask/{first['session_id']}", headers=headers).json()
        assert complete["mode"] == restored["mode"] == "ANALYSIS_COMPLETE"
        assert restored["decision"]["recommendation"]
    finally:
        engine.dispose()


def test_general_answer_and_followup_share_bounded_session_without_memory_or_decision(monkeypatch):
    client, factory, _, engine = _client(monkeypatch)
    provider = _GeneralProvider()
    monkeypatch.setattr(routes.unified_aura_orchestrator.models, "provider", provider)
    try:
        headers = {"Authorization": "Bearer test"}
        first = client.post("/personal/ask", headers=headers, json={"message": "Explain compound interest simply."})
        assert first.status_code == 200 and first.json()["mode"] == "GENERAL"
        second = client.post("/personal/ask", headers=headers, json={"session_id": first.json()["session_id"], "message": "Give me an example with $5,000."})
        assert second.status_code == 200 and len(second.json()["turns"]) == 4
        assert "Explain compound interest simply." in provider.requests[-1].prompt
        assert "A useful Aura answer." in provider.requests[-1].prompt
        db = factory()
        assert db.execute(select(memory_table)).mappings().all() == []
        assert db.execute(select(personal_decision_table)).mappings().all() == []
        report = db.execute(select(intelligence_session_table.c.report_json)).scalar_one()
        assert report["model_usage"] == {"provider":"offline","model":"general-test","input_tokens":5,"output_tokens":6,"total_tokens":11}
        db.close()
    finally:
        engine.dispose()
