from dataclasses import FrozenInstanceError, fields

import pytest

from app.simulation import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationFinding,
    SimulationInputV1,
    SimulationLimitation,
    SimulationResultV1,
    SimulationScenario,
    SimulationType,
    SimulationValidationError,
    StrategyStressResult,
    UserSimulationAssumption,
    simulation_to_dict,
    simulation_to_json,
    validate_simulation_input,
    validate_simulation_result,
)
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyRisk,
    SuccessMeasure,
)


def valid_input(**changes):
    values = {
        "objective": "Retain key customers.",
        "chosen_direction": "Stabilize service before expanding.",
        "strategic_approach": "Strengthen reliability in ordered stages.",
        "phases": (StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        "success_measures": (SuccessMeasure("Reliability remains stable.", "evidence-1"),),
        "constraints": (StrategyConstraint("continuity", "Maintain service continuity."),),
        "resources": (StrategyResource("Operations", "Owns reliability."),),
        "risks": (StrategyRisk("Capacity may remain constrained.", "Gate expansion."),),
        "strategy_assumptions": (StrategyAssumption("The team remains available.", "decision"),),
        "uncertainties": ("Demand timing remains uncertain.",),
        "change_conditions": ("Reliability declines.",),
        "time_horizon": "Next planning cycle",
        "evidence_refs": (EvidenceReference("evidence-1", "Reliability review"),),
        "scenarios": (SimulationScenario(
            "adverse-demand", "Adverse demand", "Demand rises before capacity improves.",
            ("Demand exceeds current operating capacity.",), ScenarioSource.USER_SUPPLIED,
            ScenarioSeverity.HIGH,
        ),),
        "user_assumptions": (UserSimulationAssumption("Current staffing remains fixed.", "adverse-demand"),),
    }
    values.update(changes)
    return SimulationInputV1(**values)


def finding(statement="Reliability becomes fragile.", provenance=FindingProvenance.MODEL_GENERATED):
    return SimulationFinding(statement, provenance, ("evidence-1",))


def valid_result(**changes):
    values = {
        "scenario_results": (StrategyStressResult(
            scenario_key="adverse-demand",
            elements_under_stress=(finding(),),
            plausible_effects=(finding("Expansion may need to pause."),),
            sensitivity=ScenarioSeverity.HIGH,
            constraint_conflicts=(finding("Continuity may be harder to preserve.", FindingProvenance.DERIVED),),
        ),),
        "cross_scenario_comparison": (finding("The adverse scenario creates the greatest strain.", FindingProvenance.DERIVED),),
        "assumptions_used": (finding("Current staffing remains fixed.", FindingProvenance.USER_SUPPLIED),),
        "uncertainties": (finding("Demand duration remains unknown."),),
        "limitations": (SimulationLimitation("not_calibrated", "This is scenario analysis, not calibrated forecasting."),),
        "confidence": ConfidenceLevel.MODERATE,
        "confidence_rationale": ("The stress test uses explicit but incomplete assumptions.",),
        "evidence_refs": (EvidenceReference("evidence-1", "Reliability review"),),
    }
    values.update(changes)
    return SimulationResultV1(**values)


def test_valid_strategy_stress_test_input_and_result():
    source = valid_input()
    result = valid_result()
    validate_simulation_input(source)
    validate_simulation_result(result, source)
    assert source.simulation_type is result.simulation_type is SimulationType.STRATEGY_STRESS_TEST


def test_contracts_are_frozen():
    with pytest.raises(FrozenInstanceError):
        valid_input().objective = "Changed"
    with pytest.raises(FrozenInstanceError):
        valid_result().confidence = ConfidenceLevel.HIGH


def test_empty_and_duplicate_scenarios_are_rejected():
    with pytest.raises(SimulationValidationError, match="scenarios must not be empty"):
        validate_simulation_input(valid_input(scenarios=()))
    scenario = valid_input().scenarios[0]
    with pytest.raises(SimulationValidationError, match="scenario keys must be unique"):
        validate_simulation_input(valid_input(scenarios=(scenario, scenario)))


def test_unknown_scenario_references_are_rejected():
    assumption = UserSimulationAssumption("Staffing changes.", "unknown")
    with pytest.raises(SimulationValidationError, match="scenario_key is unknown"):
        validate_simulation_input(valid_input(user_assumptions=(assumption,)))
    with pytest.raises(SimulationValidationError, match="every source scenario"):
        validate_simulation_result(valid_result(scenario_results=(StrategyStressResult(
            "unknown", (finding(),), (finding(),), ScenarioSeverity.LOW,
        ),)), valid_input())


@pytest.mark.parametrize("changes", [
    {"objective": " "},
    {"scenarios": (SimulationScenario("bad", "", "Description", ("Changed",), ScenarioSource.SYSTEM_DERIVED),)},
    {"limitations": (SimulationLimitation("not_calibrated", ""),)},
])
def test_empty_required_text_is_rejected(changes):
    if "limitations" in changes:
        with pytest.raises(SimulationValidationError, match="meaningful"):
            validate_simulation_result(valid_result(**changes), valid_input())
    else:
        with pytest.raises(SimulationValidationError, match="meaningful"):
            validate_simulation_input(valid_input(**changes))


def test_confidence_is_qualitative_only():
    validate_simulation_result(valid_result(confidence=ConfidenceLevel.LOW), valid_input())
    with pytest.raises(SimulationValidationError, match="qualitative"):
        validate_simulation_result(valid_result(confidence=0.72), valid_input())


def test_probability_and_tenant_authority_are_not_contract_fields():
    names = {item.name for item in fields(SimulationInputV1)} | {item.name for item in fields(SimulationResultV1)}
    forbidden = {
        "probability", "success_probability", "forecast_probability", "likelihood_score",
        "user_id", "organization_id", "workspace_id", "database_id", "idempotency_key",
        "provider", "model", "prompt", "credentials",
    }
    assert names.isdisjoint(forbidden)
    with pytest.raises(TypeError):
        SimulationInputV1(**{**valid_input().__dict__, "probability": 0.72})


def test_user_and_model_provenance_remain_explicit():
    source = valid_input()
    result = valid_result()
    assert source.user_assumptions[0].provenance is FindingProvenance.USER_SUPPLIED
    assert result.scenario_results[0].plausible_effects[0].provenance is FindingProvenance.MODEL_GENERATED


def test_evidence_serializes_without_internal_authority():
    payload = simulation_to_dict(valid_result())
    assert payload["evidence_refs"] == [{"evidence_id": "evidence-1", "citation_label": "Reliability review"}]
    rendered = simulation_to_json(valid_input())
    for forbidden in ("organization_id", "workspace_id", "user_id", "database_id", "provider", "prompt"):
        assert forbidden not in rendered


def test_serialization_is_deterministic():
    first = simulation_to_json(valid_input())
    second = simulation_to_json(valid_input())
    assert first == second
    assert '"schema_version":1' in first
    assert '"simulation_type":"strategy_stress_test"' in first


def test_collection_bounds_are_enforced():
    scenarios = tuple(
        SimulationScenario(f"scenario-{index}", f"Scenario {index}", "Changed condition.", ("Change",), ScenarioSource.SYSTEM_DERIVED)
        for index in range(7)
    )
    with pytest.raises(SimulationValidationError, match="scenarios exceeds 6 items"):
        validate_simulation_input(valid_input(scenarios=scenarios))


def test_invalid_evidence_reference_is_rejected():
    bad = SimulationFinding("Finding", FindingProvenance.DERIVED, ("unknown",))
    with pytest.raises(SimulationValidationError, match="evidence_ref is unknown"):
        validate_simulation_result(valid_result(cross_scenario_comparison=(bad,)), valid_input())


def test_invalid_source_provenance_and_evidence_shapes_are_rejected():
    invalid_scenario = SimulationScenario(
        "invalid-source", "Invalid source", "A changed condition.", ("Change",), "user",
    )
    with pytest.raises(SimulationValidationError, match="ScenarioSource"):
        validate_simulation_input(valid_input(scenarios=(invalid_scenario,)))
    invalid_assumption = UserSimulationAssumption(
        "Assumption", provenance=FindingProvenance.MODEL_GENERATED,
    )
    with pytest.raises(SimulationValidationError, match="USER_SUPPLIED"):
        validate_simulation_input(valid_input(user_assumptions=(invalid_assumption,)))
    invalid_finding = SimulationFinding("Finding", "model")
    with pytest.raises(SimulationValidationError, match="provenance is invalid"):
        validate_simulation_result(valid_result(uncertainties=(invalid_finding,)), valid_input())
    with pytest.raises(SimulationValidationError, match="EvidenceReference"):
        validate_simulation_input(valid_input(evidence_refs=({"evidence_id": "unsafe"},)))


def test_no_legacy_simulation_dependency():
    modules = " ".join((SimulationInputV1.__module__, SimulationResultV1.__module__))
    assert "app.lab" not in modules and "app.learning" not in modules and "aura_request" not in modules
