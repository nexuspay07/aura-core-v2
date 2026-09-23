from dataclasses import asdict
from pathlib import Path

import pytest

from app.intelligence_v2.contracts import (
    AnalysisAlternative,
    AnalysisExecution,
    AnalysisRecommendation,
    AnalysisResult,
    DecisionClassification,
    DecisionRequest,
    DecisionState,
    DecisionType,
    EvidenceItem,
    EvidenceSourceType,
)
from app.strategy.capability import StrategyCapability
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyConstraint,
    StrategyInput,
    StrategyPhase,
    StrategyResult,
    StrategyScope,
    SuccessMeasure,
)
from app.strategy.validation import StrategyValidationError


class RecordingOrchestrator:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.inputs = []

    def generate(self, strategy_input):
        self.inputs.append(strategy_input)
        if self.error:
            raise self.error
        return self.result


def direct_input():
    return StrategyInput(
        scope=StrategyScope(11, 22, 33),
        objective="Retain key customers",
        chosen_direction="Improve reliability",
        constraints=(StrategyConstraint("budget", "Stay within the approved budget."),),
        evidence_refs=(EvidenceReference("evidence-1", "Reliability review"),),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("Some execution uncertainty remains.",),
    )


def canonical_result(source):
    return StrategyResult(
        scope=source.scope,
        objective=source.objective,
        chosen_direction=source.chosen_direction,
        approach="Stabilize reliability before expanding.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        success_measures=(SuccessMeasure("Reliability improves."),),
        change_conditions=("Reliability does not improve.",),
        confidence=source.confidence,
        confidence_rationale=source.confidence_rationale,
        source_decision_id=source.source_decision_id,
        source_reference=source.source_reference,
        constraints=source.constraints,
        evidence_refs=source.evidence_refs,
    )


def decision_artifacts():
    evidence = EvidenceItem(
        id="evidence-1",
        source_type=EvidenceSourceType.USER_STATEMENT,
        source_name="authorized-user",
        citation_label="Reliability review",
    )
    request = DecisionRequest(
        user_id=11,
        organization_id=22,
        workspace_id=33,
        user_query="How should we retain customers?",
        decision_type=DecisionType.CUSTOMER_RETENTION,
        objective="Retain key customers",
        timeframe="Next planning horizon",
        constraints=["Stay within the approved budget."],
    )
    state = DecisionState(
        request=request,
        classification=DecisionClassification(
            DecisionType.CUSTOMER_RETENTION, [], 1.0, ["Explicit objective."], []
        ),
        assembled_context={},
        evidence=[evidence],
        analysis_outputs={"phase2": {"resources": [], "uncertainties": []}},
    )
    recommendation = AnalysisRecommendation(
        "Improve reliability",
        "Reliability supports retention.",
        "Customer trust improves.",
        [],
        ["Reliability does not improve."],
    )
    result = AnalysisResult(
        "Retention is threatened by reliability.",
        [],
        [],
        [AnalysisAlternative("Expand support", [], [], [], [], [])],
        "Reliability is the material factor.",
        [],
        recommendation,
        [],
        [],
        ["evidence-1"],
        [],
        [],
        [],
    )
    execution = AnalysisExecution(
        "READY", result, "MODERATE", ["Some execution uncertainty remains."], [], {}
    )
    return state, execution


def test_direct_invocation_delegates_once_returns_exact_result_and_does_not_mutate_input():
    source = direct_input()
    expected = canonical_result(source)
    orchestrator = RecordingOrchestrator(expected)
    before = asdict(source)

    actual = StrategyCapability(orchestrator).generate(source)

    assert actual is expected
    assert orchestrator.inputs == [source]
    assert orchestrator.inputs[0].scope is source.scope
    assert asdict(source) == before


def test_decision_invocation_uses_adapter_semantics_and_same_generation_path(monkeypatch):
    state, execution = decision_artifacts()
    orchestrator = RecordingOrchestrator()
    capability = StrategyCapability(orchestrator)
    generated = object()
    calls = []

    def canonical_generate(strategy_input):
        calls.append(strategy_input)
        return generated

    monkeypatch.setattr(capability, "generate", canonical_generate)
    actual = capability.generate_from_decision(
        state,
        execution,
        source_decision_id=71,
        source_reference="personal-decision:71",
    )

    assert actual is generated
    assert len(calls) == 1
    strategy_input = calls[0]
    assert strategy_input.scope == StrategyScope(11, 22, 33)
    assert strategy_input.source_decision_id == 71
    assert strategy_input.source_reference == "personal-decision:71"
    assert strategy_input.constraints == (
        StrategyConstraint("decision-constraint-001", "Stay within the approved budget."),
    )
    assert strategy_input.evidence_refs == (
        EvidenceReference("evidence-1", "Reliability review"),
    )
    assert strategy_input.confidence is ConfidenceLevel.MODERATE
    assert strategy_input.confidence_rationale == ("Some execution uncertainty remains.",)


def test_decision_invocation_delegates_to_injected_orchestrator_once():
    state, execution = decision_artifacts()
    orchestrator = RecordingOrchestrator()
    capability = StrategyCapability(orchestrator)
    expected = canonical_result(
        StrategyInput(
            scope=StrategyScope(11, 22, 33),
            objective="Retain key customers",
            chosen_direction="Improve reliability",
            confidence=ConfidenceLevel.MODERATE,
            confidence_rationale=("Some execution uncertainty remains.",),
        )
    )
    orchestrator.result = expected

    assert capability.generate_from_decision(state, execution) is expected
    assert len(orchestrator.inputs) == 1


def test_canonical_errors_propagate_unchanged():
    error = StrategyValidationError(["invalid strategy input"])
    capability = StrategyCapability(RecordingOrchestrator(error=error))

    with pytest.raises(StrategyValidationError) as raised:
        capability.generate(direct_input())

    assert raised.value is error


def test_capability_has_only_canonical_dependencies_and_no_side_effect_systems():
    source = Path("app/strategy/capability.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "fastapi",
        "sqlalchemy",
        "sessionlocal",
        "repository",
        "personal_ask",
        "marketplace",
        "commercial",
        "telemetry",
        "control_center",
        "simulation",
        "planning",
        "app.learning",
        "app.execution",
        "app.core.agents",
        "jwt",
        "membership",
    ):
        assert forbidden not in source
