from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from app.intelligence_v2.contracts import (
    AnalysisAlternative, AnalysisExecution, AnalysisRecommendation, AnalysisResult,
    AssumptionItem, AssumptionStatus, DecisionClassification, DecisionRequest,
    DecisionState, DecisionType, EvidenceItem, EvidenceSourceType,
)
from app.strategy.adapters import build_strategy_input
from app.strategy.contracts import ConfidenceLevel, StrategyInput
from app.strategy.validation import StrategyValidationError


def decision_artifacts(*, rich=False, objective="Retain key customers", chosen="Improve reliability", confidence="MODERATE"):
    evidence = EvidenceItem(
        id="evidence-1", source_type=EvidenceSourceType.USER_STATEMENT,
        source_name="user", content="PRIVATE RAW DOCUMENT BODY", citation_label="Approved budget",
    )
    request = DecisionRequest(
        user_id=11, organization_id=22 if rich else None, workspace_id=33 if rich else None,
        user_query="PRIVATE CONVERSATION AND PROMPT", decision_type=DecisionType.CUSTOMER_RETENTION,
        objective=objective, timeframe="six months" if rich else None,
        constraints=["Stay within the approved budget.", "Do not increase workload."] if rich else [],
        business_context={"memory_blob": "PRIVATE MEMORY", "database_url": "PRIVATE DATABASE URL"},
        source_metadata={"provider_raw_output": "PRIVATE PROVIDER OUTPUT", "auth_token": "PRIVATE TOKEN"},
    )
    state = DecisionState(
        request=request,
        classification=DecisionClassification(DecisionType.CUSTOMER_RETENTION, [], .8, [], []),
        assembled_context={"credentials": "PRIVATE CREDENTIAL"}, evidence=[evidence],
        assumptions=[AssumptionItem("The vendor remains available.", "user", .7, AssumptionStatus.CONFIRMED, "Delivery changes.")] if rich else [],
        analysis_outputs={"phase2": {
            "resources": [{"type": "budget", "value": "$10,000", "category": "financial", "basis": "known"}] if rich else [],
            "uncertainties": ["Renewal timing is uncertain."] if rich else [],
            "simulation_result": "PRIVATE SIMULATION",
        }}, analysis_status="READY_FOR_ANALYSIS",
    )
    alternatives = [
        AnalysisAlternative("Improve reliability", ["Retention"], ["Delay"], ["evidence-1"], [], []),
        AnalysisAlternative("Expand immediately", ["Growth"], ["Risk"], [], [], []),
    ] if rich else [AnalysisAlternative(chosen, [], [], ["evidence-1"], [], [])]
    recommendation = AnalysisRecommendation(
        chosen, "Grounded rationale", "", [],
        ["Churn remains elevated after reliability improves."] if rich else ["Material evidence changes."],
    )
    result = AnalysisResult(
        "Problem", [], ["Demand remains stable."] if rich else [], alternatives,
        "Analysis", ["Delivery may slip."] if rich else [], recommendation, [], [],
        ["evidence-1"], ["evidence-1"], [], [],
    )
    execution = AnalysisExecution("READY", result, confidence, ["Some uncertainty remains."], [], {})
    return state, execution


def test_minimal_decision_artifact_builds_valid_immutable_strategy_input():
    value = build_strategy_input(*decision_artifacts())
    assert isinstance(value, StrategyInput)
    assert value.objective == "Retain key customers"
    assert value.chosen_direction == "Improve reliability"
    assert value.resources == ()
    with pytest.raises(FrozenInstanceError): value.objective = "Changed"


def test_rich_artifact_maps_every_supported_field_without_reasoning():
    state, execution = decision_artifacts(rich=True)
    value = build_strategy_input(state, execution, source_decision_id=71, source_reference="personal-decision:71")
    assert value.scope.user_id == 11 and value.scope.organization_id == 22 and value.scope.workspace_id == 33
    assert value.source_decision_id == 71 and value.source_reference == "personal-decision:71"
    assert value.decision_type is DecisionType.CUSTOMER_RETENTION
    assert value.objective == state.request.objective
    assert value.chosen_direction == execution.result.recommendation.recommended_option
    assert [item.name for item in value.considered_alternatives] == ["Improve reliability", "Expand immediately"]
    assert [item.statement for item in value.constraints] == state.request.constraints
    assert value.resources[0].name == "budget" and value.resources[0].description == "$10,000"
    assert value.evidence_refs[0].evidence_id == "evidence-1"
    assert [item.statement for item in value.assumptions] == ["The vendor remains available.", "Demand remains stable."]
    assert value.risks[0].risk == "Delivery may slip." and value.risks[0].mitigation is None
    assert value.uncertainties == ("Renewal timing is uncertain.",)
    assert value.time_horizon == "six months"
    assert value.change_conditions == ("Churn remains elevated after reliability improves.",)
    assert value.confidence is ConfidenceLevel.MODERATE
    assert value.confidence_rationale == ("Some uncertainty remains.",)


def test_absent_source_and_tenant_parts_are_not_fabricated():
    value = build_strategy_input(*decision_artifacts())
    assert value.source_decision_id is None and value.source_reference is None
    assert value.scope.organization_id is None and value.scope.workspace_id is None


def test_constraints_have_exact_ordered_text_and_deterministic_nonsecret_ids():
    state, execution = decision_artifacts(rich=True)
    first = build_strategy_input(state, execution)
    second = build_strategy_input(state, execution)
    assert first.constraints == second.constraints
    assert [item.constraint_id for item in first.constraints] == ["decision-constraint-001", "decision-constraint-002"]
    assert [item.statement for item in first.constraints] == state.request.constraints


def test_evidence_preserves_reference_metadata_but_not_content():
    value = build_strategy_input(*decision_artifacts(rich=True))
    assert value.evidence_refs[0].citation_label == "Approved budget"
    assert "PRIVATE RAW DOCUMENT BODY" not in repr(value)


def test_alternatives_keep_decision_order_and_risks_gain_no_scores_or_mitigation():
    value = build_strategy_input(*decision_artifacts(rich=True))
    assert [item.name for item in value.considered_alternatives] == ["Improve reliability", "Expand immediately"]
    assert value.risks[0].mitigation is None
    assert {item.name for item in fields(value.risks[0])} == {"risk", "mitigation"}


@pytest.mark.parametrize("objective,chosen,error", [(" ", "Direction", "objective"), ("Objective", " ", "recommendation")])
def test_missing_required_decision_information_fails(objective, chosen, error):
    with pytest.raises(StrategyValidationError, match=error):
        build_strategy_input(*decision_artifacts(objective=objective, chosen=chosen))


def test_invalid_scope_and_confidence_fail_through_strategy_validation():
    state, execution = decision_artifacts()
    state.request.user_id = 0
    with pytest.raises(StrategyValidationError, match="scope.user_id"):
        build_strategy_input(state, execution)
    state, execution = decision_artifacts(confidence=None)
    with pytest.raises(StrategyValidationError, match="confidence"):
        build_strategy_input(state, execution)


def test_incomplete_execution_fails_instead_of_fabricating_defaults():
    state, execution = decision_artifacts()
    incomplete = AnalysisExecution("PARTIAL", None, None, [], [], {})
    with pytest.raises(StrategyValidationError, match="completed READY"):
        build_strategy_input(state, incomplete)


def test_private_and_cross_boundary_decision_state_cannot_leak():
    value = build_strategy_input(*decision_artifacts(rich=True))
    rendered = repr(value)
    for secret in ("PRIVATE CONVERSATION", "PRIVATE MEMORY", "PRIVATE PROVIDER", "PRIVATE TOKEN", "PRIVATE DATABASE", "PRIVATE CREDENTIAL", "PRIVATE SIMULATION"):
        assert secret not in rendered
    forbidden = {"simulation_result", "reward", "execution_status", "task_assignee", "tool_execution", "actual_outcome", "marketplace_publication"}
    assert {item.name for item in fields(value)}.isdisjoint(forbidden)


def test_adapter_has_no_provider_database_network_or_persistence_dependencies():
    source = Path("app/strategy/adapters.py").read_text(encoding="utf-8")
    for forbidden in ("model_provider", "SessionLocal", "requests", "httpx", "socket", ".commit(", ".execute("):
        assert forbidden not in source
