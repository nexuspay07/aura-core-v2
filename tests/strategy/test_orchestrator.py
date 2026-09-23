from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.model_provider import ProviderTimeoutError, ProviderUnavailableError
from app.strategy.contracts import (
    ConfidenceLevel, EvidenceReference, StrategyAlternative, StrategyAssumption,
    StrategyConstraint, StrategyInput, StrategyResource, StrategyRisk, StrategyScope,
)
from app.strategy.model_schema import STRATEGY_SCHEMA_NAME, strategy_model_schema
from app.strategy.orchestrator import StrategyGenerationError, StrategyOrchestrator
from app.strategy.validation import StrategyValidationError


class RecordingProvider:
    provider_name = "recording"
    model_name = "offline"
    capabilities = {"structured_output"}

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return response, {"provider": "recording"}

    def health_check(self):
        return True


def valid_model_output(**changes):
    value = {
        "approach": "Stabilize the service before expanding the selected direction.",
        "phases": [{
            "order": 1,
            "name": "Stabilize",
            "purpose": "Reduce the known reliability risk before broader expansion.",
            "focus_areas": ["Reliability", "Customer retention"],
            "milestone_intent": "Reliability is observably improved.",
        }],
        "risk_mitigations": [],
        "success_measures": ["Reliability improves without exceeding the approved constraints."],
        "assumptions": [],
        "uncertainties": [],
        "change_conditions": ["Reliability does not improve."],
    }
    value.update(changes)
    return value


def minimal_input(**changes):
    value = {
        "scope": StrategyScope(1),
        "objective": "Retain key customers",
        "chosen_direction": "Improve service reliability",
        "confidence": ConfidenceLevel.MODERATE,
        "confidence_rationale": ("Some execution uncertainty remains.",),
    }
    value.update(changes)
    return StrategyInput(**value)


def rich_input(**changes):
    value = {
        "scope": StrategyScope(11, 22, 33),
        "source_decision_id": 71,
        "source_reference": "personal-decision:71",
        "decision_type": DecisionType.CUSTOMER_RETENTION,
        "objective": "Retain key customers",
        "chosen_direction": "Improve service reliability",
        "considered_alternatives": (
            StrategyAlternative("Expand now", "Expand immediately"),
            StrategyAlternative("Stabilize first", "Improve reliability before expansion"),
        ),
        "constraints": (StrategyConstraint("budget", "Stay within the approved $10,000 budget."),),
        "resources": (StrategyResource("team", "Existing reliability team"),),
        "evidence_refs": (EvidenceReference("evidence-1", "Reliability review"),),
        "assumptions": (StrategyAssumption("The vendor remains available.", "decision"),),
        "risks": (StrategyRisk("Delivery may slip."),),
        "uncertainties": ("Renewal timing is uncertain.",),
        "time_horizon": "six months",
        "change_conditions": ("Customer churn remains elevated.",),
        "confidence": ConfidenceLevel.MODERATE,
        "confidence_rationale": ("Some execution uncertainty remains.",),
    }
    value.update(changes)
    return StrategyInput(**value)


def generate(strategy_input=None, output=None):
    provider = RecordingProvider(output or valid_model_output())
    result = StrategyOrchestrator(provider).generate(strategy_input or minimal_input())
    return result, provider


def test_minimal_input_produces_valid_immutable_strategy_result():
    result, provider = generate()
    assert result.objective == "Retain key customers"
    assert result.chosen_direction == "Improve service reliability"
    assert [phase.order for phase in result.phases] == [1]
    assert result.success_measures
    assert len(provider.calls) == 1
    with pytest.raises(FrozenInstanceError): result.approach = "changed"


def test_rich_input_preserves_authoritative_fields_and_synthesizes_mitigation():
    source = rich_input()
    output = valid_model_output(
        risk_mitigations=[{"risk_index": 0, "mitigation": "Stage expansion behind a reliability review."}],
        assumptions=["The current team can sequence stabilization work."],
        uncertainties=["The timing of improvement remains uncertain."],
        change_conditions=["The reliability review identifies a different primary cause."],
    )
    result, _ = generate(source, output)
    assert result.scope == source.scope
    assert result.source_decision_id == 71 and result.source_reference == "personal-decision:71"
    assert result.objective == source.objective and result.chosen_direction == source.chosen_direction
    assert result.constraints == source.constraints and result.evidence_refs == source.evidence_refs
    assert result.resources == source.resources and result.alternatives == source.considered_alternatives
    assert result.confidence == source.confidence and result.confidence_rationale == source.confidence_rationale
    assert result.risks == (StrategyRisk("Delivery may slip.", "Stage expansion behind a reliability review."),)
    assert result.assumptions[-1].source == "strategy_generation"
    assert result.change_conditions[:1] == source.change_conditions


def test_strategy_schema_name_and_schema_are_passed_on_strict_structured_path():
    _, provider = generate()
    call = provider.calls[0]
    assert call["schema_name"] == STRATEGY_SCHEMA_NAME == "strategy_result"
    assert call["output_schema"] == strategy_model_schema()
    assert call["output_schema"]["additionalProperties"] is False
    assert call["timeout_seconds"] >= 10 and call["reasoning_effort"] == "medium"


def test_bounded_payload_has_only_strategy_descriptions_and_no_trusted_ids():
    source = rich_input()
    _, provider = generate(source)
    payload = provider.calls[0]["payload"]
    assert set(payload) == {
        "objective", "chosen_direction", "constraints", "resources", "assumptions",
        "risks", "uncertainties", "time_horizon", "change_conditions", "alternatives",
        "confidence", "confidence_rationale",
    }
    rendered = repr(payload)
    for forbidden in ("user_id", "organization_id", "workspace_id", "source_decision_id", "source_reference", "evidence_id", "constraint_id", "citation_label"):
        assert forbidden not in rendered


def test_provider_schema_excludes_authoritative_and_cross_boundary_fields():
    rendered = repr(strategy_model_schema())
    for forbidden in (
        "objective", "chosen_direction", "scope", "user_id", "organization_id",
        "workspace_id", "source_decision_id", "evidence_id", "constraint_id",
        "confidence", "simulation", "execution", "outcome", "reward", "marketplace",
    ):
        assert forbidden not in rendered


def test_result_has_no_simulation_execution_outcome_rl_or_marketplace_state():
    names = {item.name for item in fields(generate()[0])}
    forbidden = {"simulation_result", "execution_status", "actual_outcome", "reward", "rl_state", "marketplace_publication"}
    assert names.isdisjoint(forbidden)


def test_invalid_input_fails_before_provider_invocation():
    provider = RecordingProvider(valid_model_output())
    with pytest.raises(StrategyValidationError, match="objective"):
        StrategyOrchestrator(provider).generate(minimal_input(objective=" "))
    assert provider.calls == []


@pytest.mark.parametrize("error", [
    ProviderUnavailableError("unavailable"),
    ProviderTimeoutError("timeout", "timeout"),
])
def test_provider_availability_failures_are_explicit_and_not_hidden(error):
    provider = RecordingProvider(error)
    with pytest.raises(type(error)):
        StrategyOrchestrator(provider).generate(minimal_input())
    assert len(provider.calls) == 1


@pytest.mark.parametrize("output,match", [
    ("not-an-object", "object"),
    ({}, "missing fields"),
    (valid_model_output(approach=""), "approach"),
    (valid_model_output(phases=[]), "phases"),
    (valid_model_output(phases=[{"order": 2, "name": "Late", "purpose": "Late phase", "focus_areas": [], "milestone_intent": None}]), "phase order"),
    (valid_model_output(success_measures=[]), "success measure"),
    (valid_model_output(assumptions=[""]), "assumptions item"),
])
def test_invalid_structured_outputs_fail_after_one_bounded_retry(output, match):
    provider = RecordingProvider(output)
    with pytest.raises(StrategyGenerationError, match=match):
        StrategyOrchestrator(provider).generate(minimal_input())
    assert len(provider.calls) == 2
    assert provider.calls[1]["reasoning_effort"] == "low"


@pytest.mark.parametrize("field,value", [
    ("objective", "Replace objective"),
    ("chosen_direction", "Choose something else"),
    ("scope", {"user_id": 999}),
    ("source_decision_id", 999),
    ("constraints", []),
    ("evidence_refs", ["invented"]),
    ("confidence", "HIGH"),
])
def test_provider_cannot_replace_or_generate_authoritative_fields(field, value):
    output = valid_model_output(**{field: value})
    provider = RecordingProvider(output)
    with pytest.raises(StrategyGenerationError, match="forbidden fields"):
        StrategyOrchestrator(provider).generate(rich_input())
    assert len(provider.calls) == 2


def test_risk_mitigation_cannot_create_or_duplicate_risks():
    unknown = valid_model_output(risk_mitigations=[{"risk_index": 1, "mitigation": "Invented"}])
    with pytest.raises(StrategyGenerationError, match="unknown risk"):
        StrategyOrchestrator(RecordingProvider(unknown)).generate(rich_input())
    duplicate = valid_model_output(risk_mitigations=[
        {"risk_index": 0, "mitigation": "First"}, {"risk_index": 0, "mitigation": "Second"},
    ])
    with pytest.raises(StrategyGenerationError, match="unique"):
        StrategyOrchestrator(RecordingProvider(duplicate)).generate(rich_input())


def test_unsupported_numeric_targets_fail_but_grounded_numbers_are_allowed():
    invented = valid_model_output(success_measures=["Increase revenue by 37%."])
    with pytest.raises(StrategyGenerationError, match="unsupported numeric"):
        StrategyOrchestrator(RecordingProvider(invented)).generate(rich_input())
    grounded = valid_model_output(success_measures=["Stay within the approved $10,000 budget."])
    result = StrategyOrchestrator(RecordingProvider(grounded)).generate(rich_input())
    assert "$10,000" in result.success_measures[0].condition


def test_valid_first_response_is_one_call_and_retry_is_capped_at_two():
    _, provider = generate()
    assert len(provider.calls) == 1
    retry_provider = RecordingProvider({}, valid_model_output())
    result = StrategyOrchestrator(retry_provider).generate(minimal_input())
    assert result.approach and len(retry_provider.calls) == 2
    assert StrategyOrchestrator.max_provider_calls == 2


def test_model_cannot_merely_repeat_chosen_direction():
    output = valid_model_output(approach="Improve service reliability")
    with pytest.raises(StrategyGenerationError, match="develop rather than repeat"):
        StrategyOrchestrator(RecordingProvider(output)).generate(minimal_input())


def test_orchestrator_is_platform_independent_and_has_no_forbidden_dependencies():
    source = Path("app/strategy/orchestrator.py").read_text(encoding="utf-8")
    for forbidden in (
        "fastapi", "sessionlocal", "personal_ask", "control_center", "simulation",
        "app.learning", "app.execution", "app.core.agents", "marketplace", "requests", "httpx",
    ):
        assert forbidden not in source.lower()
    assert StrategyOrchestrator(RecordingProvider(valid_model_output())).generate(minimal_input())
