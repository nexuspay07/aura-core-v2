from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.strategy.routes as routes
from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.services.telemetry_service import IntelligenceExecutionTelemetry
from app.services.telemetry_service import telemetry_service
from app.services import control_center_service
from app.db.database import metadata
import app.db.schema  # noqa: F401 - register the complete test metadata graph
from app.strategy.contracts import (
    ConfidenceLevel,
    StrategyAssumption,
    StrategyPhase,
    StrategyResult,
    StrategyRisk,
    SuccessMeasure,
)
from app.strategy.quality import StrategyQualityError, StrategyQualityIssue
from app.strategy.validation import StrategyValidationError


PRIVATE_VALUES = (
    "PRIVATE OBJECTIVE",
    "PRIVATE DIRECTION",
    "PRIVATE CONSTRAINT",
    "PRIVATE RESOURCE",
    "PRIVATE ASSUMPTION",
    "PRIVATE RISK",
    "PRIVATE MITIGATION",
    "PRIVATE PHASE",
    "PRIVATE SUCCESS",
    "PRIVATE UNCERTAINTY",
    "PRIVATE CHANGE",
    "PRIVATE EVIDENCE",
    "PRIVATE CITATION",
    "PRIVATE PROMPT",
    "PRIVATE PROVIDER RESPONSE",
    "private@example.com",
    "Private Person",
)


def payload():
    return {
        "objective": PRIVATE_VALUES[0],
        "chosen_direction": PRIVATE_VALUES[1],
        "constraints": [PRIVATE_VALUES[2]],
        "resources": [{"name": PRIVATE_VALUES[3], "description": "PRIVATE RESOURCE DESCRIPTION"}],
        "assumptions": [PRIVATE_VALUES[4]],
        "risks": [{"risk": PRIVATE_VALUES[5], "mitigation": PRIVATE_VALUES[6]}],
        "uncertainties": [PRIVATE_VALUES[9]],
        "time_horizon": "PRIVATE TIME HORIZON",
        "change_conditions": [PRIVATE_VALUES[10]],
    }


def result_for(strategy_input):
    return StrategyResult(
        scope=strategy_input.scope,
        objective=strategy_input.objective,
        chosen_direction=strategy_input.chosen_direction,
        approach="PRIVATE APPROACH",
        phases=(StrategyPhase(1, PRIVATE_VALUES[7], "PRIVATE PHASE PURPOSE"),),
        risks=(StrategyRisk(PRIVATE_VALUES[5], PRIVATE_VALUES[6]),),
        success_measures=(SuccessMeasure(PRIVATE_VALUES[8]),),
        assumptions=strategy_input.assumptions + (
            StrategyAssumption("PRIVATE GENERATED ASSUMPTION", "strategy_generation"),
        ),
        uncertainties=strategy_input.uncertainties,
        change_conditions=strategy_input.change_conditions,
        confidence=ConfidenceLevel.LOW,
        confidence_rationale=(),
    )


class Capability:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def generate(self, strategy_input):
        self.calls += 1
        if self.error:
            raise self.error
        return result_for(strategy_input)


def setup(monkeypatch, capability):
    events = []

    async def identity(_):
        return {
            "user": {"id": 11, "email": PRIVATE_VALUES[14], "full_name": PRIVATE_VALUES[15]},
            "organization": {"id": 22},
            "workspace": {"id": 33},
        }

    monkeypatch.setattr(routes, "get_current_user_from_token", identity)
    monkeypatch.setattr(routes, "strategy_capability", capability)
    monkeypatch.setattr(routes, "_record_terminal_execution", events.append)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), events


def test_success_emits_one_content_free_operational_event(monkeypatch):
    capability = Capability()
    client, events = setup(monkeypatch, capability)
    response = client.post("/strategies", headers={"Authorization": "Bearer token"}, json=payload())

    assert response.status_code == 200
    assert capability.calls == 1
    assert len(events) == 1
    event = events[0]
    assert event.route == "/strategies"
    assert event.request_mode == "direct_strategy"
    assert event.outcome == "success" and event.error_category is None
    assert event.latency_ms >= 0 and event.request_id
    assert (event.user_id, event.organization_id, event.workspace_id) == (11, 22, 33)
    assert event.provider is None and event.model is None
    assert event.input_tokens is None and event.output_tokens is None
    assert event.reasoning_tokens is None and event.total_tokens is None
    assert event.retry_count is None and event.provider_call_count is None
    rendered = str(event.model_dump())
    for private in (*PRIVATE_VALUES, "PRIVATE RESOURCE DESCRIPTION", "PRIVATE TIME HORIZON", "PRIVATE APPROACH"):
        assert private not in rendered


@pytest.mark.parametrize(
    ("error", "status_code", "category"),
    [
        (StrategyValidationError(["PRIVATE OBJECTIVE"]), 422, "validation_failure"),
        (StrategyQualityError([StrategyQualityIssue("private", "PRIVATE PHASE", "approach")]), 422, "quality_failure"),
        (InvalidModelResponseError("PRIVATE PROVIDER RESPONSE"), 502, "provider_invalid_response"),
        (ProviderUnavailableError("PRIVATE PROVIDER RESPONSE"), 503, "provider_unavailable"),
        (ProviderTimeoutError("PRIVATE PROVIDER RESPONSE"), 504, "provider_timeout"),
    ],
)
def test_failures_emit_one_safe_category_without_changing_http_behavior(
    monkeypatch, error, status_code, category
):
    capability = Capability(error)
    client, events = setup(monkeypatch, capability)
    response = client.post("/strategies", headers={"Authorization": "Bearer token"}, json=payload())

    assert response.status_code == status_code
    assert capability.calls == 1 and len(events) == 1
    assert events[0].outcome == "failure"
    assert events[0].error_category == category
    rendered = str(events[0].model_dump())
    assert "PRIVATE" not in rendered


def test_internal_failure_is_content_free_and_reraised(monkeypatch):
    capability = Capability(RuntimeError("PRIVATE STRATEGY RESULT"))
    client, events = setup(monkeypatch, capability)
    with pytest.raises(RuntimeError, match="PRIVATE STRATEGY RESULT"):
        client.post("/strategies", headers={"Authorization": "Bearer token"}, json=payload())
    assert len(events) == 1 and events[0].error_category == "internal_failure"
    assert "PRIVATE" not in str(events[0].model_dump())


def test_personal_scope_uses_existing_nullable_identity_policy(monkeypatch):
    capability = Capability()
    events = []

    async def identity(_):
        return {"user": {"id": 11}, "organization": None, "workspace": None}

    monkeypatch.setattr(routes, "get_current_user_from_token", identity)
    monkeypatch.setattr(routes, "strategy_capability", capability)
    monkeypatch.setattr(routes, "_record_terminal_execution", events.append)
    app = FastAPI()
    app.include_router(routes.router)
    response = TestClient(app).post(
        "/strategies", headers={"Authorization": "Bearer token"}, json=payload()
    )
    assert response.status_code == 200
    assert events[0].organization_id is None and events[0].workspace_id is None


def test_telemetry_writer_failure_does_not_break_success(monkeypatch):
    class Database:
        rolled_back = False
        closed = False

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    database = Database()
    monkeypatch.setattr(routes, "SessionLocal", lambda: database)
    monkeypatch.setattr(
        routes.telemetry_service,
        "record_intelligence_execution",
        lambda *_: (_ for _ in ()).throw(RuntimeError("PRIVATE DATABASE ERROR")),
    )
    event = IntelligenceExecutionTelemetry(
        request_id="safe-request-id",
        user_id=11,
        organization_id=None,
        workspace_id=None,
        route="/strategies",
        request_mode="direct_strategy",
        outcome="success",
        latency_ms=1,
    )
    routes._record_terminal_execution(event)
    assert database.rolled_back and database.closed


def test_strategy_event_flows_through_existing_control_center_aggregation():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    metadata.create_all(engine)
    database = sessionmaker(bind=engine)()
    try:
        telemetry_service.record_intelligence_execution(database, IntelligenceExecutionTelemetry(
            request_id="strategy-request",
            user_id=11,
            organization_id=None,
            workspace_id=None,
            route="/strategies",
            request_mode="direct_strategy",
            outcome="success",
            latency_ms=7,
        ))
        now = datetime.now(timezone.utc)
        report = control_center_service.intelligence(
            database, now - timedelta(minutes=1), now + timedelta(minutes=1), "24h"
        )
        assert report["total_requests"] == 1
        assert report["routes"] == [{"key": "/strategies", "count": 1}]
        assert report["modes"] == [{"key": "direct_strategy", "count": 1}]
        assert report["outcomes"] == [{"key": "success", "count": 1}]
    finally:
        database.close()
        engine.dispose()
