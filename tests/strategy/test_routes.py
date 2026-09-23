from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.strategy.routes as routes
from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.strategy.contracts import (
    ConfidenceLevel,
    StrategyAssumption,
    StrategyPhase,
    StrategyResult,
    StrategyRisk,
    SuccessMeasure,
)
from app.strategy.capability import StrategyCapability
from app.strategy.orchestrator import StrategyOrchestrator
from app.strategy.presentation import to_strategy_presentation
from app.strategy.quality import StrategyQualityError, StrategyQualityIssue
from app.strategy.validation import StrategyValidationError, validate_strategy_input


class RecordingCapability:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.inputs = []

    def generate(self, strategy_input):
        self.inputs.append(strategy_input)
        if self.error:
            raise self.error
        return self.result


def identity():
    return {
        "user": {"id": 11},
        "organization": {"id": 22},
        "workspace": {"id": 33},
    }


def request_payload():
    return {
        "objective": "Retain key customers.",
        "chosen_direction": "Improve reliability before expansion.",
        "constraints": ["Stay within the approved budget."],
        "resources": [{"name": "Delivery team", "description": "Existing capacity."}],
        "assumptions": ["The vendor remains available."],
        "risks": [{"risk": "Delivery may slip.", "mitigation": "Use staged reviews."}],
        "uncertainties": ["Future demand remains uncertain."],
        "time_horizon": "Next planning horizon",
        "change_conditions": ["Reliability does not improve."],
    }


def canonical_result(strategy_input):
    return StrategyResult(
        scope=strategy_input.scope,
        objective=strategy_input.objective,
        chosen_direction=strategy_input.chosen_direction,
        approach="Stabilize critical dependencies before expanding.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        constraints=strategy_input.constraints,
        resources=strategy_input.resources,
        risks=(StrategyRisk("Delivery may slip.", "Use staged reviews."),),
        success_measures=(SuccessMeasure("Reliability improves."),),
        assumptions=strategy_input.assumptions + (
            StrategyAssumption("The team can sequence the work.", "strategy_generation"),
        ),
        uncertainties=strategy_input.uncertainties,
        change_conditions=strategy_input.change_conditions,
        confidence=strategy_input.confidence,
        confidence_rationale=strategy_input.confidence_rationale,
        time_horizon=strategy_input.time_horizon,
    )


def client(monkeypatch, capability):
    async def authenticated(_):
        return identity()

    monkeypatch.setattr(routes, "get_current_user_from_token", authenticated)
    monkeypatch.setattr(routes, "strategy_capability", capability)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), app


def test_anonymous_request_is_rejected(monkeypatch):
    test_client, _ = client(monkeypatch, RecordingCapability())
    assert test_client.post("/strategies", json=request_payload()).status_code in {401, 403}


def test_authenticated_request_maps_scope_and_content_and_invokes_capability_once(monkeypatch):
    capability = RecordingCapability()

    def generate(strategy_input):
        capability.inputs.append(strategy_input)
        return canonical_result(strategy_input)

    capability.generate = generate
    test_client, _ = client(monkeypatch, capability)
    response = test_client.post(
        "/strategies", headers={"Authorization": "Bearer token"}, json=request_payload()
    )

    assert response.status_code == 200, response.text
    assert len(capability.inputs) == 1
    value = capability.inputs[0]
    assert asdict(value.scope) == {"user_id": 11, "organization_id": 22, "workspace_id": 33}
    assert value.objective == request_payload()["objective"]
    assert value.chosen_direction == request_payload()["chosen_direction"]
    assert tuple(item.statement for item in value.constraints) == tuple(request_payload()["constraints"])
    assert [(item.name, item.description) for item in value.resources] == [("Delivery team", "Existing capacity.")]
    assert [(item.statement, item.source) for item in value.assumptions] == [("The vendor remains available.", "user_provided")]
    assert [(item.risk, item.mitigation) for item in value.risks] == [("Delivery may slip.", "Use staged reviews.")]
    assert value.uncertainties == ("Future demand remains uncertain.",)
    assert value.time_horizon == "Next planning horizon"
    assert value.change_conditions == ("Reliability does not improve.",)
    assert value.confidence is ConfidenceLevel.LOW
    assert value.confidence_rationale == (routes.DIRECT_STRATEGY_CONFIDENCE_RATIONALE,)
    assert value.evidence_refs == ()
    assert value.source_decision_id is None and value.source_reference is None


def test_direct_mapper_produces_deterministic_valid_low_confidence_input():
    body = routes.DirectStrategyRequest.model_validate(request_payload())
    scope = routes.StrategyScope(user_id=11, organization_id=22, workspace_id=33)

    first = routes.to_strategy_input(body, scope)
    second = routes.to_strategy_input(body, scope)

    validate_strategy_input(first)
    assert first.confidence is ConfidenceLevel.LOW
    assert first.confidence_rationale == second.confidence_rationale
    assert first.confidence_rationale == (routes.DIRECT_STRATEGY_CONFIDENCE_RATIONALE,)
    rationale = first.confidence_rationale[0].casefold()
    assert "directly" in rationale and "user-supplied" in rationale
    assert "without a completed decision intelligence evaluation" in rationale
    assert "evidence" not in rationale


def test_http_path_crosses_real_canonical_validation_before_offline_provider(monkeypatch):
    class OfflineProvider:
        provider_name = "offline"
        model_name = "offline"
        capabilities = {"structured_output"}

        def __init__(self):
            self.calls = []

        def generate_structured(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "approach": "Stabilize critical dependencies before expanding.",
                "phases": [{
                    "order": 1,
                    "name": "Stabilize",
                    "purpose": "Reduce reliability risk.",
                    "focus_areas": [],
                    "milestone_intent": None,
                }],
                "risk_mitigations": [],
                "success_measures": ["Reliability improves."],
                "assumptions": [],
                "uncertainties": [],
                "change_conditions": [],
            }, {}

    provider = OfflineProvider()
    capability = StrategyCapability(StrategyOrchestrator(provider))
    test_client, _ = client(monkeypatch, capability)

    response = test_client.post(
        "/strategies", headers={"Authorization": "Bearer token"}, json=request_payload()
    )

    assert response.status_code == 200, response.text
    assert len(provider.calls) == 1
    assert provider.calls[0]["payload"]["confidence"] == "LOW"
    assert provider.calls[0]["payload"]["confidence_rationale"] == [
        routes.DIRECT_STRATEGY_CONFIDENCE_RATIONALE
    ]


def test_response_uses_presentation_mapper_and_excludes_internal_fields(monkeypatch):
    capability = RecordingCapability()
    mapper_calls = []

    def generate(strategy_input):
        return canonical_result(strategy_input)

    def mapper(result):
        mapper_calls.append(result)
        return to_strategy_presentation(result)

    capability.generate = generate
    monkeypatch.setattr(routes, "to_strategy_presentation", mapper)
    test_client, _ = client(monkeypatch, capability)
    response = test_client.post(
        "/strategies", headers={"Authorization": "Bearer token"}, json=request_payload()
    )

    body = response.json()
    assert response.status_code == 200 and len(mapper_calls) == 1
    assert body["phases"][0]["name"] == "Stabilize"
    assert body["risks"] == [{"risk": "Delivery may slip.", "mitigation": "Use staged reviews."}]
    assert body["success_measures"][0]["condition"] == "Reliability improves."
    assert [item["source"] for item in body["assumptions"]] == ["user_provided", "strategy_generation"]
    assert body["uncertainties"] == ["Future demand remains uncertain."]
    assert body["change_conditions"] == ["Reliability does not improve."]
    assert body["confidence"] == "LOW"
    assert body["source_decision_id"] is None
    assert body["source_reference"] is None
    for forbidden in ("scope", "user_id", "organization_id", "workspace_id", "provider", "model", "strategy_id"):
        assert forbidden not in body


def test_request_cannot_supply_tenant_or_source_identity(monkeypatch):
    test_client, _ = client(monkeypatch, RecordingCapability())
    headers = {"Authorization": "Bearer token"}
    for field in (
        "user_id", "organization_id", "workspace_id", "source_decision_id", "evidence_refs",
        "confidence", "confidence_rationale",
    ):
        payload = {**request_payload(), field: 999}
        assert test_client.post("/strategies", headers=headers, json=payload).status_code == 422


def test_identity_without_authorized_workspace_uses_personal_scope(monkeypatch):
    capability = RecordingCapability()
    capability.generate = lambda value: capability.inputs.append(value) or canonical_result(value)

    async def personal_identity(_):
        return {"user": {"id": 11}, "organization": None, "workspace": None}

    monkeypatch.setattr(routes, "get_current_user_from_token", personal_identity)
    monkeypatch.setattr(routes, "strategy_capability", capability)
    app = FastAPI()
    app.include_router(routes.router)
    response = TestClient(app).post(
        "/strategies", headers={"Authorization": "Bearer token"}, json=request_payload()
    )
    assert response.status_code == 200
    assert capability.inputs[0].scope.organization_id is None
    assert capability.inputs[0].scope.workspace_id is None


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (StrategyValidationError(["private validation detail"]), 422),
        (StrategyQualityError([StrategyQualityIssue("private.code", "private reason", "private.path")]), 422),
        (ProviderUnavailableError("private provider detail"), 503),
        (ProviderTimeoutError("private timeout detail"), 504),
        (InvalidModelResponseError("private model output"), 502),
    ],
)
def test_errors_are_safely_translated(monkeypatch, error, expected_status):
    test_client, _ = client(monkeypatch, RecordingCapability(error=error))
    response = test_client.post(
        "/strategies", headers={"Authorization": "Bearer token"}, json=request_payload()
    )
    assert response.status_code == expected_status
    assert "private" not in response.text


def test_endpoint_is_documented_as_ephemeral_generation(monkeypatch):
    test_client, app = client(monkeypatch, RecordingCapability())
    operation = app.openapi()["paths"]["/strategies"]["post"]
    assert operation["summary"] == "Develop a strategy for a chosen direction"
    assert "get" not in app.openapi()["paths"]["/strategies"]
    assert test_client.get("/strategies", headers={"Authorization": "Bearer token"}).status_code == 405


def test_route_has_no_persistence_marketplace_telemetry_or_direct_provider_dependency():
    source = Path("app/strategy/routes.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "sqlalchemy", "repository", "marketplace",
        "commercial", "billing", "openai", "generate_structured", "personal_ask",
        "generate_from_decision", "simulation", "planning", "app.learning", "app.execution",
    ):
        assert forbidden not in source
