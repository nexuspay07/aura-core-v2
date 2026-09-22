from dataclasses import FrozenInstanceError, fields

import pytest

from app.strategy.contracts import (
    ConfidenceLevel, EvidenceReference, StrategyAssumption, StrategyConstraint,
    StrategyInput, StrategyPhase, StrategyResult, StrategyRisk, StrategyScope,
    SuccessMeasure,
)
from app.strategy.validation import StrategyValidationError, validate_strategy_input, validate_strategy_result


def source(**changes):
    values = dict(scope=StrategyScope(1, 2, 3), objective="Reduce customer churn",
                  chosen_direction="Improve reliability before expansion",
                  constraints=(StrategyConstraint("budget", "Stay within the approved budget."),),
                  evidence_refs=(EvidenceReference("e-1"),),
                  confidence=ConfidenceLevel.MODERATE,
                  confidence_rationale=("Execution uncertainty remains.",))
    values.update(changes)
    return StrategyInput(**values)


def result(**changes):
    values = dict(scope=StrategyScope(1, 2, 3), objective="Reduce customer churn",
                  chosen_direction="Improve reliability before expansion",
                  approach="Stabilize the service, then expand deliberately.",
                  phases=(StrategyPhase(1, "Stabilize", "Remove the principal reliability bottlenecks."),),
                  success_measures=(SuccessMeasure("Reliability improves without exceeding the approved budget."),),
                  change_conditions=("Customer churn continues after reliability improves.",),
                  constraints=(StrategyConstraint("budget", "Stay within the approved budget."),),
                  evidence_refs=(EvidenceReference("e-1"),),
                  confidence=ConfidenceLevel.MODERATE,
                  confidence_rationale=("Execution uncertainty remains.",))
    values.update(changes)
    return StrategyResult(**values)


def test_minimal_valid_result_and_observable_measure():
    validate_strategy_result(result(), source())


def test_multi_phase_result_requires_contiguous_supplied_order():
    phases=(StrategyPhase(1, "Stabilize", "Improve reliability."), StrategyPhase(2, "Expand", "Scale the proven approach."))
    validate_strategy_result(result(phases=phases))


@pytest.mark.parametrize("phases", [
    (StrategyPhase(1, "One", "First."), StrategyPhase(1, "Again", "Duplicate.")),
    (StrategyPhase(2, "Late", "Does not start at one."),),
    (StrategyPhase(1, "First", "First."), StrategyPhase(3, "Third", "Gap.")),
])
def test_invalid_or_duplicate_phase_order_fails(phases):
    with pytest.raises(StrategyValidationError): validate_strategy_result(result(phases=phases))


def test_constraint_preservation_passes_and_missing_constraint_fails():
    validate_strategy_result(result(), source())
    with pytest.raises(StrategyValidationError, match="does not preserve constraints"):
        validate_strategy_result(result(constraints=()), source())


def test_completed_result_needs_success_measure_but_not_numeric_target():
    validate_strategy_result(result(success_measures=(SuccessMeasure("Customers report a more reliable experience."),)))
    with pytest.raises(StrategyValidationError, match="success measure"):
        validate_strategy_result(result(success_measures=()))


def test_risk_mitigation_is_optional_but_cannot_be_blank():
    validate_strategy_result(result(risks=(StrategyRisk("Delivery may slip."), StrategyRisk("Costs may rise.", "Review scope."))))
    with pytest.raises(StrategyValidationError, match="risks require"):
        validate_strategy_result(result(risks=(StrategyRisk("Costs may rise.", "  "),)))


def test_assumptions_are_explicit_and_structurally_valid():
    validate_strategy_input(source(assumptions=(StrategyAssumption("The vendor remains available.", "decision"),)))
    with pytest.raises(StrategyValidationError, match="assumptions require"):
        validate_strategy_input(source(assumptions=(StrategyAssumption("The vendor remains available.", ""),)))


def test_change_conditions_are_required_and_structurally_valid():
    with pytest.raises(StrategyValidationError, match="change condition"):
        validate_strategy_result(result(change_conditions=()))
    with pytest.raises(StrategyValidationError, match="change_conditions"):
        validate_strategy_input(source(change_conditions=(" ",)))


def test_confidence_accepts_existing_values_and_rejects_strings():
    for confidence in ConfidenceLevel:
        validate_strategy_input(source(confidence=confidence))
    with pytest.raises(StrategyValidationError, match="ConfidenceLevel"):
        validate_strategy_input(source(confidence="MEDIUM"))


def test_source_decision_and_evidence_references_are_preserved():
    input_value=source(source_decision_id=42)
    output=result(source_decision_id=42, evidence_refs=input_value.evidence_refs)
    validate_strategy_result(output, input_value)
    assert output.source_decision_id == 42 and output.evidence_refs == input_value.evidence_refs


def test_source_decision_mismatch_fails():
    with pytest.raises(StrategyValidationError, match="source_decision_id"):
        validate_strategy_result(result(source_decision_id=8), source(source_decision_id=7))


def test_result_is_frozen_and_has_no_cross_boundary_fields():
    value=result()
    with pytest.raises(FrozenInstanceError): value.approach="Changed"
    forbidden={"simulation_result", "reward", "execution_status", "task_assignee", "tool_execution", "actual_outcome", "marketplace_publication"}
    assert {item.name for item in fields(StrategyResult)}.isdisjoint(forbidden)
