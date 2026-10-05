from dataclasses import replace
from pathlib import Path

import pytest

from app.intelligence_v2.model_provider import InvalidModelResponseError
from app.simulation import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationExecutionInputV1,
    SimulationGenerationError,
    SimulationInputV1,
    SimulationOrchestrator,
    SimulationQualityError,
    SimulationScenario,
    SimulationSourceProvenanceV1,
    SimulationValidationError,
    UserSimulationAssumption,
)
from app.simulation.model_schema import SIMULATION_SCHEMA_NAME, simulation_model_schema
from app.simulation.prompts import simulation_repair_instruction
from app.strategy.contracts import (
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyRisk,
    SuccessMeasure,
)


class RecordingProvider:
    provider_name = "recording"
    model_name = "offline"
    capabilities = {"structured_output"}

    def __init__(self, *responses):
        self.responses = responses
        self.calls = []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return response, {"provider": "recording"}

    def health_check(self):
        return True


def execution_input(**changes):
    source = SimulationInputV1(
        objective="Retain private enterprise customers within a $1,500 budget.",
        chosen_direction="Stabilize service before expanding.",
        strategic_approach="Strengthen reliability over 30 days.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        success_measures=(SuccessMeasure("Reliability remains stable.", "evidence-1"),),
        scenarios=(
            SimulationScenario(
                "adverse", "Adverse", "Demand rises before capacity improves.",
                ("Demand exceeds capacity.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.HIGH,
            ),
            SimulationScenario(
                "favorable", "Favorable", "Reliability improves before expansion.",
                ("Service reliability improves.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.LOW,
            ),
        ),
        constraints=(StrategyConstraint("continuity", "Maintain service continuity."),),
        risks=(StrategyRisk("Capacity may remain constrained.", "Gate expansion."),),
        strategy_assumptions=(StrategyAssumption("The core team remains available.", "decision"),),
        user_assumptions=(UserSimulationAssumption("Staffing remains fixed.", "adverse"),),
        uncertainties=("Demand timing remains uncertain.",),
        change_conditions=("Reliability declines.",),
        evidence_refs=(EvidenceReference("evidence-1", "Private reliability review"),),
    )
    source = replace(source, **changes)
    return SimulationExecutionInputV1(
        SimulationSourceProvenanceV1(
            "a126b09a-1060-42f9-b8f8-5e0d95309fea", 7, 1,
        ),
        source,
    )


def model_finding(statement, provenance="MODEL_GENERATED", evidence=None):
    return {
        "statement": statement,
        "provenance": provenance,
        "evidence_refs": ["evidence-1"] if evidence is None else evidence,
    }


def model_scenario(key, label):
    return {
        "scenario_key": key,
        "elements_under_stress": [model_finding(f"{label} capacity is under stress.")],
        "plausible_effects": [model_finding(f"{label} service effects may emerge.")],
        "sensitivity": "HIGH" if key == "adverse" else "LOW",
        "constraint_conflicts": [model_finding("continuity", "SOURCE")],
        "risk_observations": [model_finding("Capacity may remain constrained.", "SOURCE")],
        "mitigation_observations": [],
        "phase_sensitivities": [model_finding("Stabilize", "SOURCE")],
        "upside_conditions": [],
        "downside_conditions": [],
        "change_condition_triggers": [model_finding("Reliability declines.", "SOURCE")],
    }


def valid_output(**changes):
    value = {
        "scenario_results": [model_scenario("adverse", "Adverse"), model_scenario("favorable", "Favorable")],
        "cross_scenario_comparison": [model_finding("The adverse case strains capacity more than the favorable case.", "DERIVED")],
        "assumptions_used": [
            model_finding("The core team remains available.", "SOURCE"),
            model_finding("Staffing remains fixed.", "USER_SUPPLIED"),
        ],
        "uncertainties": [model_finding("Recovery timing remains uncertain.")],
        "confidence": "MODERATE",
        "confidence_rationale": ["The scenarios are explicit but incomplete."],
        "evidence_refs": ["evidence-1"],
    }
    value.update(changes)
    return value


def probability_output():
    value = valid_output()
    value["scenario_results"][0]["plausible_effects"] = [
        model_finding("There is a 70% chance of disruption."),
    ]
    return value


def run(*responses, source=None):
    provider = RecordingProvider(*(responses or (valid_output(),)))
    result = SimulationOrchestrator(provider).run(source or execution_input())
    return result, provider


def test_valid_provider_response_produces_canonical_result_in_one_call():
    result, provider = run()
    assert len(provider.calls) == 1
    assert result.scenario_results[0].scenario_key == "adverse"
    assert result.simulation_type.value == "strategy_stress_test"
    assert result.schema_version == 1


def test_schema_is_strict_supplied_and_has_no_probability_field():
    _, provider = run()
    call = provider.calls[0]
    assert call["schema_name"] == SIMULATION_SCHEMA_NAME
    assert call["output_schema"] == simulation_model_schema(
        ("adverse", "favorable"), ("evidence-1",),
    )
    assert call["output_schema"]["additionalProperties"] is False
    assert "probability" not in repr(call["output_schema"]).casefold()


@pytest.mark.parametrize("field,value", [
    ("simulation_type", "other"),
    ("schema_version", 99),
    ("provenance", {"strategy_revision": 99}),
    ("user_id", 41),
    ("database_id", 52),
])
def test_provider_cannot_control_system_or_authority_fields(field, value):
    provider = RecordingProvider(valid_output(**{field: value}))
    with pytest.raises(SimulationGenerationError) as error:
        SimulationOrchestrator(provider).run(execution_input())
    assert error.value.code == "simulation_generation.unexpected_fields"
    assert len(provider.calls) == 2


def test_aevric_assembles_required_system_limitation():
    result, _ = run()
    assert [(item.code, item.provenance) for item in result.limitations] == [
        ("not_calibrated", FindingProvenance.SYSTEM),
    ]


@pytest.mark.parametrize("scenario_results", [
    [model_scenario("adverse", "Adverse")],
    [model_scenario("adverse", "Adverse"), model_scenario("unknown", "Unknown")],
    [model_scenario("adverse", "First"), model_scenario("adverse", "Second")],
])
def test_provider_must_return_every_requested_scenario_exactly_once(scenario_results):
    provider = RecordingProvider(valid_output(scenario_results=scenario_results))
    with pytest.raises((SimulationValidationError, SimulationQualityError)):
        SimulationOrchestrator(provider).run(execution_input())
    assert len(provider.calls) == 2


def mutate_source_reference(section, statement):
    output = valid_output()
    output["scenario_results"][0][section] = [model_finding(statement, "SOURCE")]
    return output


@pytest.mark.parametrize("output, expected", [
    (valid_output(evidence_refs=["invented"]), SimulationGenerationError),
    (mutate_source_reference("phase_sensitivities", "Phase 7"), SimulationQualityError),
    (mutate_source_reference("constraint_conflicts", "invented constraint"), SimulationQualityError),
    (mutate_source_reference("change_condition_triggers", "invented trigger"), SimulationQualityError),
])
def test_untrusted_source_references_are_rejected(output, expected):
    provider = RecordingProvider(output)
    with pytest.raises(expected):
        SimulationOrchestrator(provider).run(execution_input())
    assert len(provider.calls) == 2


@pytest.mark.parametrize("claim", [
    "There is a 70% chance of disruption.",
    "This is guaranteed to succeed.",
])
def test_predictive_claims_are_rejected(claim):
    output = valid_output()
    output["scenario_results"][0]["plausible_effects"] = [model_finding(claim)]
    provider = RecordingProvider(output)
    with pytest.raises(SimulationQualityError):
        SimulationOrchestrator(provider).run(execution_input())
    assert len(provider.calls) == 2


def test_ordinary_numeric_strategy_content_remains_allowed():
    output = valid_output()
    output["scenario_results"][0]["plausible_effects"] = [
        model_finding("The $1,500 budget may remain available over 30 days."),
    ]
    result, _ = run(output)
    assert "$1,500" in result.scenario_results[0].plausible_effects[0].statement


def test_quality_failure_then_valid_repair_uses_exactly_two_calls():
    bad = valid_output()
    bad["scenario_results"][0]["plausible_effects"] = [model_finding("There is a 70% chance of disruption.")]
    result, provider = run(bad, valid_output())
    assert result.confidence.value == "MODERATE"
    assert len(provider.calls) == 2
    assert "simulation.numeric_probability" in provider.calls[1]["system"]


def test_malformed_response_then_valid_repair_uses_exactly_two_calls():
    result, provider = run({}, valid_output())
    assert result.scenario_results
    assert len(provider.calls) == 2
    assert "simulation_generation.missing_fields" in provider.calls[1]["system"]


@pytest.mark.parametrize("responses,error_type", [
    ((probability_output(), probability_output()), SimulationQualityError),
    (({}, {}), SimulationGenerationError),
])
def test_two_repairable_failures_stop_at_two_calls(responses, error_type):
    provider = RecordingProvider(*responses)
    with pytest.raises(error_type):
        SimulationOrchestrator(provider).run(execution_input())
    assert len(provider.calls) == 2


def test_invalid_trusted_input_makes_zero_provider_calls():
    provider = RecordingProvider(valid_output())
    invalid = execution_input(scenarios=())
    with pytest.raises(SimulationValidationError):
        SimulationOrchestrator(provider).run(invalid)
    assert provider.calls == []


def test_programming_exception_is_not_retried():
    provider = RecordingProvider(RuntimeError("programming defect"))
    with pytest.raises(RuntimeError, match="programming defect"):
        SimulationOrchestrator(provider).run(execution_input())
    assert len(provider.calls) == 1


def test_invalid_provider_response_error_is_repairable_once():
    result, provider = run(
        InvalidModelResponseError("private provider body", "invalid_json"),
        valid_output(),
    )
    assert result.scenario_results and len(provider.calls) == 2
    assert "simulation_generation.provider_response" in provider.calls[1]["system"]
    assert "private provider body" not in provider.calls[1]["system"]


def test_repair_instruction_is_deterministic_and_privacy_safe():
    first = simulation_repair_instruction(
        category="quality_validation",
        codes=("simulation.numeric_probability", "simulation.duplicate_finding"),
    )
    second = simulation_repair_instruction(
        category="quality_validation",
        codes=("simulation.duplicate_finding", "simulation.numeric_probability"),
    )
    assert first == second
    assert "Retain private" not in first and "Demand rises" not in first


def test_same_provider_response_produces_same_canonical_result():
    first, _ = run(valid_output())
    second, _ = run(valid_output())
    assert first == second


def test_provider_payload_contains_analysis_but_no_authority_or_database_ids():
    _, provider = run()
    payload = provider.calls[0]["payload"]
    assert payload["objective"].startswith("Retain")
    assert "provenance" not in payload
    rendered = repr(payload)
    for forbidden in (
        "user_id", "organization_id", "workspace_id", "owner_user_id",
        "source_decision_id", "source_decision_snapshot_id", "strategy_public_id",
        "strategy_revision", "database_id", "credentials",
    ):
        assert forbidden not in rendered


def test_orchestrator_has_no_random_persistence_http_or_legacy_dependency():
    sources = " ".join(
        Path(path).read_text(encoding="utf-8").casefold()
        for path in (
            "app/simulation/orchestrator.py",
            "app/simulation/model_schema.py",
            "app/simulation/prompts.py",
        )
    )
    for forbidden in (
        "import random", "sqlalchemy", "sessionlocal", "fastapi", "requests",
        "httpx", "app.lab", "simulationstate", "worldengine", "predictionengine",
        "aura_request", "simulation_history", "reinforcement", "experience replay",
    ):
        assert forbidden not in sources
