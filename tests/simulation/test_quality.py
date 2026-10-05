from dataclasses import asdict, replace
from pathlib import Path

import pytest

from app.simulation import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationExecutionInputV1,
    SimulationFinding,
    SimulationInputV1,
    SimulationLimitation,
    SimulationQualityError,
    SimulationResultV1,
    SimulationScenario,
    SimulationSourceProvenanceV1,
    SimulationValidationError,
    StrategyStressResult,
    UserSimulationAssumption,
    validate_simulation_result_quality,
)
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyRisk,
    SuccessMeasure,
)


def execution_input(*, scenarios=None):
    scenario_values = scenarios or (
        SimulationScenario(
            "adverse", "Adverse", "Demand rises before capacity improves.",
            ("Demand exceeds capacity.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.HIGH,
        ),
        SimulationScenario(
            "favorable", "Favorable", "Reliability improves before expansion.",
            ("Service reliability improves.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.LOW,
        ),
    )
    source = SimulationInputV1(
        objective="Retain private enterprise customers.",
        chosen_direction="Stabilize service before expanding.",
        strategic_approach="Strengthen reliability in ordered stages.",
        phases=(
            StrategyPhase(1, "Stabilize", "Reduce reliability risk."),
            StrategyPhase(2, "Expand", "Scale the reliable service."),
        ),
        success_measures=(SuccessMeasure("Reliability remains stable.", "evidence-1"),),
        scenarios=scenario_values,
        constraints=(StrategyConstraint("continuity", "Maintain service continuity."),),
        risks=(StrategyRisk("Capacity may remain constrained.", "Gate expansion."),),
        strategy_assumptions=(StrategyAssumption("The core team remains available.", "decision"),),
        uncertainties=("Demand timing remains uncertain.",),
        change_conditions=("Reliability declines.",),
        evidence_refs=(EvidenceReference("evidence-1", "Private reliability review"),),
        user_assumptions=(UserSimulationAssumption("Staffing remains fixed.", "adverse"),),
    )
    return SimulationExecutionInputV1(
        SimulationSourceProvenanceV1(
            "a126b09a-1060-42f9-b8f8-5e0d95309fea", 1, 1,
        ),
        source,
    )


def finding(statement, provenance=FindingProvenance.MODEL_GENERATED):
    return SimulationFinding(statement, provenance, ("evidence-1",))


def scenario_result(key, label):
    return StrategyStressResult(
        scenario_key=key,
        elements_under_stress=(finding(f"{label} operating capacity is under stress."),),
        plausible_effects=(finding(f"{label} service effects may emerge."),),
        sensitivity=ScenarioSeverity.HIGH if key == "adverse" else ScenarioSeverity.LOW,
        constraint_conflicts=(finding("continuity", FindingProvenance.SOURCE),),
        risk_observations=(finding("Capacity may remain constrained.", FindingProvenance.SOURCE),),
        phase_sensitivities=(finding("Stabilize", FindingProvenance.SOURCE),),
        change_condition_triggers=(finding("Reliability declines.", FindingProvenance.SOURCE),),
    )


def valid_result(**changes):
    values = dict(
        scenario_results=(scenario_result("adverse", "Adverse"), scenario_result("favorable", "Favorable")),
        cross_scenario_comparison=(finding("The adverse case strains capacity more than the favorable case."),),
        assumptions_used=(
            finding("The core team remains available.", FindingProvenance.SOURCE),
            finding("Staffing remains fixed.", FindingProvenance.USER_SUPPLIED),
            finding("Recovery work can be sequenced.", FindingProvenance.MODEL_GENERATED),
        ),
        uncertainties=(finding("Recovery timing remains uncertain."),),
        limitations=(SimulationLimitation("not_calibrated", "This is scenario analysis, not calibrated forecasting."),),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("The scenarios are explicit but incomplete.",),
        evidence_refs=(EvidenceReference("evidence-1", "Private reliability review"),),
    )
    values.update(changes)
    return SimulationResultV1(**values)


def codes(error):
    return {item.code for item in error.value.issues}


def replace_scenario(result, index, **changes):
    values = list(result.scenario_results)
    values[index] = replace(values[index], **changes)
    return replace(result, scenario_results=tuple(values))


def test_fully_valid_result_passes_with_valid_evidence_and_provenance():
    validate_simulation_result_quality(execution_input(), valid_result())


@pytest.mark.parametrize("scenario_results", [
    (scenario_result("adverse", "Adverse"),),
    (scenario_result("adverse", "Adverse"), scenario_result("unknown", "Unknown")),
])
def test_missing_or_unknown_scenario_fails_coverage(scenario_results):
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), valid_result(scenario_results=scenario_results))
    assert "simulation.scenario_coverage" in codes(error)


def test_duplicate_scenario_is_rejected_by_structural_layer():
    duplicate = scenario_result("adverse", "Duplicate")
    with pytest.raises(SimulationValidationError, match="scenario result keys must be unique"):
        validate_simulation_result_quality(
            execution_input(), valid_result(scenario_results=(duplicate, duplicate)),
        )


def test_unsupported_evidence_fails_and_supported_evidence_passes():
    validate_simulation_result_quality(execution_input(), valid_result())
    unsupported = replace(
        valid_result(),
        evidence_refs=(EvidenceReference("evidence-1"), EvidenceReference("invented")),
    )
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), unsupported)
    assert "simulation.unsupported_evidence" in codes(error)


@pytest.mark.parametrize("section, valid_text, invalid_text, code", [
    ("phase_sensitivities", "Phase 1", "Phase 7", "simulation.phase_reference"),
    ("constraint_conflicts", "continuity", "invented constraint", "simulation.constraint_reference"),
    ("change_condition_triggers", "Reliability declines.", "Invented trigger", "simulation.change_condition_reference"),
])
def test_source_references_must_exist(section, valid_text, invalid_text, code):
    valid = replace_scenario(
        valid_result(), 0, **{section: (finding(valid_text, FindingProvenance.SOURCE),)},
    )
    validate_simulation_result_quality(execution_input(), valid)
    invalid = replace_scenario(
        valid_result(), 0, **{section: (finding(invalid_text, FindingProvenance.SOURCE),)},
    )
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), invalid)
    assert code in codes(error)


def test_assumption_provenance_preserves_source_user_and_model_boundaries():
    validate_simulation_result_quality(execution_input(), valid_result())
    misuse = replace(
        valid_result(),
        assumptions_used=(finding("Staffing remains fixed.", FindingProvenance.SOURCE),),
    )
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), misuse)
    assert "simulation.assumption_provenance" in codes(error)


def test_obvious_finding_provenance_misuse_fails():
    bad = replace_scenario(
        valid_result(), 0,
        plausible_effects=(finding("A newly generated effect.", FindingProvenance.SOURCE),),
    )
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), bad)
    assert "simulation.invalid_finding_provenance" in codes(error)


@pytest.mark.parametrize("claim", [
    "There is a 70% chance of disruption.",
    "There is a 70 percent chance of disruption.",
    "The probability of 0.7 implies disruption.",
    "Likelihood: 80% under this scenario.",
    "The success probability is material.",
])
def test_numeric_probability_claims_fail(claim):
    bad = replace_scenario(valid_result(), 0, plausible_effects=(finding(claim),))
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), bad)
    assert "simulation.numeric_probability" in codes(error)


@pytest.mark.parametrize("ordinary", [
    "The $1,500 budget remains available.",
    "Recovery may take 30 days.",
    "The plan has 3 phases and 20 employees.",
])
def test_ordinary_numeric_content_is_preserved(ordinary):
    candidate = replace_scenario(valid_result(), 0, plausible_effects=(finding(ordinary),))
    validate_simulation_result_quality(execution_input(), candidate)


@pytest.mark.parametrize("claim, code", [
    ("This is guaranteed to succeed.", "simulation.predictive_certainty"),
    ("This is a guaranteed outcome.", "simulation.predictive_certainty"),
    ("The model predicts severe disruption.", "simulation.forecast_claim"),
    ("Expected return will be $5,000.", "simulation.forecast_claim"),
])
def test_forecast_and_predictive_certainty_claims_fail(claim, code):
    bad = replace_scenario(valid_result(), 0, plausible_effects=(finding(claim),))
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), bad)
    assert code in codes(error)


def test_non_forecast_limitation_is_required_by_stable_code():
    validate_simulation_result_quality(execution_input(), valid_result())
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(
            execution_input(),
            valid_result(limitations=(SimulationLimitation("scope", "Only supplied scenarios were considered."),)),
        )
    assert "simulation.missing_non_forecast_limitation" in codes(error)


@pytest.mark.parametrize("statements", [
    ("Duplicate finding.", "Duplicate finding."),
    (" Duplicate   Finding ", "duplicate finding"),
])
def test_duplicate_findings_fail_after_conservative_normalization(statements):
    findings = tuple(finding(item) for item in statements)
    bad = replace_scenario(valid_result(), 0, plausible_effects=findings)
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), bad)
    assert "simulation.duplicate_finding" in codes(error)


def test_distinct_findings_pass():
    candidate = replace_scenario(
        valid_result(), 0,
        plausible_effects=(finding("Capacity tightens."), finding("Expansion pauses.")),
    )
    validate_simulation_result_quality(execution_input(), candidate)


def test_repeated_core_analysis_across_materially_different_scenarios_fails():
    repeated = scenario_result("adverse", "Generic")
    second = replace(repeated, scenario_key="favorable")
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(
            execution_input(), valid_result(scenario_results=(repeated, second)),
        )
    assert "simulation.scenario_repetition" in codes(error)


def test_overlapping_risk_does_not_make_distinct_scenarios_fail():
    candidate = valid_result()
    assert candidate.scenario_results[0].risk_observations == candidate.scenario_results[1].risk_observations
    validate_simulation_result_quality(execution_input(), candidate)


def test_cross_scenario_comparison_must_add_comparative_content():
    bad = replace(
        valid_result(),
        cross_scenario_comparison=(finding("Demand rises before capacity improves."),),
    )
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), bad)
    assert "simulation.cross_scenario_comparison" in codes(error)


def test_validation_is_deterministic_and_does_not_mutate_values():
    source, result = execution_input(), valid_result()
    before_source, before_result = asdict(source), asdict(result)
    validate_simulation_result_quality(source, result)
    validate_simulation_result_quality(source, result)
    assert asdict(source) == before_source
    assert asdict(result) == before_result


def test_quality_errors_are_stable_and_privacy_safe():
    private = "Private customer Alpha will definitely succeed."
    bad = replace_scenario(valid_result(), 0, plausible_effects=(finding(private),))
    with pytest.raises(SimulationQualityError) as error:
        validate_simulation_result_quality(execution_input(), bad)
    assert error.value.issues[0].code.startswith("simulation.")
    rendered = str(error.value)
    for private_value in (
        private, "Retain private enterprise customers.", "Staffing remains fixed.",
        "evidence-1", "Private reliability review", "41", "52", "63",
    ):
        assert private_value not in rendered


def test_quality_validator_is_provider_persistence_http_random_and_legacy_free():
    source = Path("app/simulation/quality.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "modelprovider", "generate_structured", "openai", "fastapi", "sqlalchemy",
        "sessionlocal", "requests", "httpx", "random", "app.lab", "worldengine",
        "predictionengine", "aura_request", "simulation_history",
    ):
        assert forbidden not in source
