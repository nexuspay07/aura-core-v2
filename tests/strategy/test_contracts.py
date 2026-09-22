from dataclasses import FrozenInstanceError, fields

import pytest

from app.intelligence_v2.contracts import DecisionType
from app.strategy.contracts import (
    ConfidenceLevel, EvidenceReference, StrategyConstraint, StrategyInput,
    StrategyScope,
)
from app.strategy.validation import validate_strategy_input


def minimal_input(**changes):
    values = dict(
        scope=StrategyScope(user_id=1), objective="Retain key customers",
        chosen_direction="Improve service reliability", confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("Some operating uncertainty remains.",),
    )
    values.update(changes)
    return StrategyInput(**values)


def test_minimal_valid_strategy_input():
    validate_strategy_input(minimal_input())


def test_rich_input_preserves_scope_evidence_and_source():
    value = minimal_input(
        scope=StrategyScope(1, 2, 3), source_decision_id=17,
        decision_type=DecisionType.STRATEGIC_PLANNING,
        constraints=(StrategyConstraint("budget", "Stay within the approved budget."),),
        evidence_refs=(EvidenceReference("evidence-1", "Budget approval"),),
        change_conditions=("Reliability does not improve.",),
    )
    validate_strategy_input(value)
    assert value.source_decision_id == 17
    assert value.evidence_refs[0].evidence_id == "evidence-1"
    assert value.scope.organization_id == 2 and value.scope.workspace_id == 3


def test_optional_organization_and_workspace_are_valid():
    validate_strategy_input(minimal_input(scope=StrategyScope(user_id=1)))


def test_contracts_are_frozen_and_collections_are_immutable():
    value = minimal_input()
    with pytest.raises(FrozenInstanceError):
        value.objective = "Changed"
    assert isinstance(value.constraints, tuple)


def test_contract_boundary_has_no_cross_system_fields():
    names = {item.name for item in fields(StrategyInput)}
    forbidden = {"simulation_result", "reward", "execution_status", "task_assignee", "tool_execution", "actual_outcome", "marketplace_publication"}
    assert names.isdisjoint(forbidden)
