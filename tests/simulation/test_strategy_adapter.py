from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

from app.simulation import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationAdapterError,
    SimulationExecutionInputV1,
    SimulationScenario,
    SimulationSourceType,
    SimulationValidationError,
    UserSimulationAssumption,
    build_simulation_input_from_strategy_revision,
    simulation_to_dict,
    simulation_to_json,
)
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyResult,
    StrategyRisk,
    StrategyScope,
    SuccessMeasure,
)


STRATEGY_ID = "a126b09a-1060-42f9-b8f8-5e0d95309fea"


def strategy_revision(*, revision=1, objective="Retain key customers."):
    return StrategyResult(
        scope=StrategyScope(user_id=41, organization_id=52, workspace_id=63),
        objective=objective,
        chosen_direction="Stabilize service before expanding.",
        approach="Strengthen reliability in ordered stages.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk.", ("Operations",), "Stable service"),),
        success_measures=(SuccessMeasure("Reliability remains stable.", "evidence-1"),),
        change_conditions=("Reliability declines.",),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("Evidence is useful but incomplete.",),
        strategy_id=STRATEGY_ID,
        source_decision_id=777,
        source_reference="personal-decision:public-reference",
        constraints=(StrategyConstraint("continuity", "Maintain service continuity."),),
        assumptions=(StrategyAssumption("The team remains available.", "decision"),),
        resources=(StrategyResource("Operations", "Owns reliability."),),
        risks=(StrategyRisk("Capacity may remain constrained.", "Gate expansion."),),
        uncertainties=("Demand timing remains uncertain.",),
        evidence_refs=(EvidenceReference("evidence-1", "Reliability review"),),
        time_horizon="Next planning cycle",
        version=revision,
    )


def scenario():
    return SimulationScenario(
        "adverse-demand",
        "Adverse demand",
        "Demand rises before capacity improves.",
        ("Demand exceeds current capacity.",),
        ScenarioSource.USER_SUPPLIED,
        ScenarioSeverity.HIGH,
    )


def build(strategy=None, *, scenarios=None, assumptions=None, schema_version=1):
    return build_simulation_input_from_strategy_revision(
        strategy or strategy_revision(),
        strategy_schema_version=schema_version,
        scenarios=(scenario(),) if scenarios is None else scenarios,
        user_assumptions=() if assumptions is None else assumptions,
    )


def test_maps_strategy_revision_fields_exactly_without_mutating_meaning():
    source = strategy_revision()
    result = build(source)
    value = result.simulation_input

    assert value.objective == source.objective
    assert value.chosen_direction == source.chosen_direction
    assert value.strategic_approach == source.approach
    assert value.phases == source.phases
    assert value.success_measures == source.success_measures
    assert value.constraints == source.constraints
    assert value.resources == source.resources
    assert value.risks == source.risks
    assert value.strategy_assumptions == source.assumptions
    assert value.uncertainties == source.uncertainties
    assert value.change_conditions == source.change_conditions
    assert value.time_horizon == source.time_horizon
    assert value.evidence_refs == source.evidence_refs
    assert value.scenarios == (scenario(),)


def test_user_assumptions_remain_separate_and_user_supplied():
    assumption = UserSimulationAssumption("Staffing remains fixed.", "adverse-demand")
    result = build(assumptions=[assumption]).simulation_input
    assert result.user_assumptions == (assumption,)
    assert result.user_assumptions[0].provenance is FindingProvenance.USER_SUPPLIED
    assert result.strategy_assumptions == strategy_revision().assumptions


def test_provenance_pins_public_strategy_revision_and_schema():
    provenance = build().provenance
    assert provenance.source_type is SimulationSourceType.STRATEGY_REVISION
    assert provenance.strategy_public_id == STRATEGY_ID
    assert provenance.strategy_revision == 1
    assert provenance.strategy_schema_version == 1


def test_provider_facing_input_excludes_authority_database_and_source_identity():
    execution = build()
    analytical_fields = {item.name for item in fields(execution.simulation_input)}
    forbidden = {
        "strategy_id", "strategy_public_id", "strategy_revision", "strategy_revision_id",
        "source_decision_id", "source_decision_snapshot_id", "owner_user_id", "user_id",
        "organization_id", "workspace_id", "account_type", "roles", "permissions",
        "provider", "model", "credentials", "random_seed",
    }
    assert analytical_fields.isdisjoint(forbidden)
    assert forbidden.isdisjoint(set(simulation_to_dict(execution.simulation_input)))
    provenance_json = simulation_to_json(execution.provenance)
    for internal in ("source_decision_id", "source_decision_snapshot_id", "database_id"):
        assert internal not in provenance_json


def test_revision_one_remains_revision_one_when_revision_two_exists():
    revision_one = strategy_revision(revision=1, objective="Content A")
    revision_two = strategy_revision(revision=2, objective="Content B")
    first = build(revision_one)
    second = build(revision_two)
    assert first.provenance.strategy_revision == 1
    assert first.simulation_input.objective == "Content A"
    assert second.provenance.strategy_revision == 2
    assert second.simulation_input.objective == "Content B"


def test_execution_serialization_is_deterministic_and_revision_sensitive():
    first = build()
    equivalent = build(strategy_revision())
    revised = build(strategy_revision(revision=2))
    changed = build(strategy_revision(objective="Enter a new market."))
    assert simulation_to_json(first) == simulation_to_json(equivalent)
    assert simulation_to_json(first) != simulation_to_json(revised)
    assert simulation_to_json(first) != simulation_to_json(changed)


def test_invalid_scenario_fails_through_canonical_validation():
    invalid = SimulationScenario("Bad Key", "Invalid", "Invalid key.", ("Changed",), ScenarioSource.USER_SUPPLIED)
    with pytest.raises(SimulationValidationError, match="stable lowercase key"):
        build(scenarios=[invalid])


@pytest.mark.parametrize("changes, message", [
    ({"strategy_id": None}, "public UUID"),
    ({"strategy_id": "not-a-uuid"}, "public UUID"),
    ({"version": None}, "exact positive revision"),
])
def test_exact_persisted_revision_identity_is_required(changes, message):
    with pytest.raises(SimulationAdapterError, match=message):
        build(replace(strategy_revision(), **changes))


def test_schema_version_must_be_positive():
    with pytest.raises(SimulationAdapterError, match="strategy_schema_version"):
        build(schema_version=0)


def test_inputs_are_snapshotted_and_contracts_are_immutable():
    scenarios = [scenario()]
    assumptions = [UserSimulationAssumption("Staffing remains fixed.", "adverse-demand")]
    source = strategy_revision()
    execution = build(source, scenarios=scenarios, assumptions=assumptions)
    scenarios.clear()
    assumptions.clear()

    assert execution.simulation_input.scenarios == (scenario(),)
    assert len(execution.simulation_input.user_assumptions) == 1
    assert source == strategy_revision()
    with pytest.raises(FrozenInstanceError):
        execution.provenance.strategy_revision = 2
    with pytest.raises(FrozenInstanceError):
        execution.simulation_input.objective = "Changed"
    assert isinstance(execution, SimulationExecutionInputV1)


def test_adapter_has_no_provider_random_persistence_or_legacy_dependency():
    source = (Path(__file__).parents[2] / "app" / "simulation" / "adapters.py").read_text(encoding="utf-8")
    forbidden = (
        "model_provider", "random", "sqlalchemy", "StrategyRepository", "app.lab",
        "AuraRequest", "WorldEngine", "PredictionEngine", "reinforcement", "experience_replay",
    )
    assert all(item not in source for item in forbidden)
