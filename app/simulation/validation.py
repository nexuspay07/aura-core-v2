"""Pure deterministic validation for canonical Simulation V1 contracts."""

from __future__ import annotations

import re

from app.simulation.contracts import (
    FindingProvenance,
    SIMULATION_SCHEMA_VERSION,
    ScenarioSeverity,
    ScenarioSource,
    SimulationFinding,
    SimulationInputV1,
    SimulationLimitation,
    SimulationResultV1,
    SimulationScenario,
    SimulationType,
    StrategyStressResult,
    UserSimulationAssumption,
)
from app.strategy.contracts import ConfidenceLevel
from app.strategy.contracts import (
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyRisk,
    SuccessMeasure,
)


MAX_SCENARIOS = 6
MAX_SOURCE_ITEMS = 50
MAX_USER_ASSUMPTIONS = 30
MAX_FINDINGS_PER_SECTION = 50
MAX_TEXT_LENGTH = 4000
_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class SimulationValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def _text(value: object, name: str, errors: list[str], *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name} must be meaningful")
    elif len(value) > MAX_TEXT_LENGTH:
        errors.append(f"{name} exceeds {MAX_TEXT_LENGTH} characters")


def _bounded(values: object, name: str, maximum: int, errors: list[str], *, required: bool = False) -> tuple:
    if not isinstance(values, tuple):
        errors.append(f"{name} must be a tuple")
        return ()
    if required and not values:
        errors.append(f"{name} must not be empty")
    if len(values) > maximum:
        errors.append(f"{name} exceeds {maximum} items")
    return values


def _metadata(value: object, errors: list[str]) -> None:
    if getattr(value, "schema_version", None) != SIMULATION_SCHEMA_VERSION:
        errors.append("schema_version must identify Simulation V1")
    if getattr(value, "simulation_type", None) is not SimulationType.STRATEGY_STRESS_TEST:
        errors.append("simulation_type must be strategy_stress_test")


def _evidence(values: tuple, name: str, errors: list[str]) -> set[str]:
    identifiers = []
    for index, item in enumerate(_bounded(values, name, MAX_SOURCE_ITEMS, errors)):
        if not isinstance(item, EvidenceReference):
            errors.append(f"{name}[{index}] must be an EvidenceReference")
            continue
        _text(getattr(item, "evidence_id", None), f"{name}[{index}].evidence_id", errors)
        _text(getattr(item, "citation_label", None), f"{name}[{index}].citation_label", errors, optional=True)
        identifiers.append(getattr(item, "evidence_id", ""))
    if len(identifiers) != len(set(identifiers)):
        errors.append(f"{name} identifiers must be unique")
    return set(identifiers)


def validate_simulation_input(value: SimulationInputV1) -> None:
    if not isinstance(value, SimulationInputV1):
        raise SimulationValidationError(["value must be a SimulationInputV1"])
    errors: list[str] = []
    _metadata(value, errors)
    for name in ("objective", "chosen_direction", "strategic_approach"):
        _text(getattr(value, name), name, errors)
    _text(value.time_horizon, "time_horizon", errors, optional=True)

    phases = _bounded(value.phases, "phases", 20, errors, required=True)
    orders = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, StrategyPhase):
            errors.append(f"phases[{index}] must be a StrategyPhase")
            continue
        if not isinstance(phase.order, int) or isinstance(phase.order, bool) or phase.order <= 0:
            errors.append(f"phases[{index}].order must be a positive integer")
        else:
            orders.append(phase.order)
        _text(phase.name, f"phases[{index}].name", errors)
        _text(phase.purpose, f"phases[{index}].purpose", errors)
    if orders != list(range(1, len(phases) + 1)):
        errors.append("phases must be in contiguous order starting at 1")

    measures = _bounded(value.success_measures, "success_measures", MAX_SOURCE_ITEMS, errors, required=True)
    constraints = _bounded(value.constraints, "constraints", MAX_SOURCE_ITEMS, errors)
    resources = _bounded(value.resources, "resources", MAX_SOURCE_ITEMS, errors)
    risks = _bounded(value.risks, "risks", MAX_SOURCE_ITEMS, errors)
    assumptions = _bounded(value.strategy_assumptions, "strategy_assumptions", MAX_SOURCE_ITEMS, errors)
    uncertainties = _bounded(value.uncertainties, "uncertainties", MAX_SOURCE_ITEMS, errors)
    changes = _bounded(value.change_conditions, "change_conditions", MAX_SOURCE_ITEMS, errors)
    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, StrategyConstraint):
            errors.append(f"constraints[{index}] must be a StrategyConstraint")
            continue
        _text(constraint.constraint_id, f"constraints[{index}].constraint_id", errors)
        _text(constraint.statement, f"constraints[{index}].statement", errors)
    for index, resource in enumerate(resources):
        if not isinstance(resource, StrategyResource):
            errors.append(f"resources[{index}] must be a StrategyResource")
            continue
        _text(resource.name, f"resources[{index}].name", errors)
        _text(resource.description, f"resources[{index}].description", errors)
    for index, risk in enumerate(risks):
        if not isinstance(risk, StrategyRisk):
            errors.append(f"risks[{index}] must be a StrategyRisk")
            continue
        _text(risk.risk, f"risks[{index}].risk", errors)
        _text(risk.mitigation, f"risks[{index}].mitigation", errors, optional=True)
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, StrategyAssumption):
            errors.append(f"strategy_assumptions[{index}] must be a StrategyAssumption")
            continue
        _text(assumption.statement, f"strategy_assumptions[{index}].statement", errors)
        _text(assumption.source, f"strategy_assumptions[{index}].source", errors)
    for name, values in (("uncertainties", uncertainties), ("change_conditions", changes)):
        for index, item in enumerate(values):
            _text(item, f"{name}[{index}]", errors)
    evidence_ids = _evidence(value.evidence_refs, "evidence_refs", errors)

    scenarios = _bounded(value.scenarios, "scenarios", MAX_SCENARIOS, errors, required=True)
    scenario_keys = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, SimulationScenario):
            errors.append(f"scenarios[{index}] must be a SimulationScenario")
            continue
        _text(scenario.key, f"scenarios[{index}].key", errors)
        if isinstance(scenario.key, str) and not _KEY.fullmatch(scenario.key):
            errors.append(f"scenarios[{index}].key must be a stable lowercase key")
        _text(scenario.name, f"scenarios[{index}].name", errors)
        _text(scenario.description, f"scenarios[{index}].description", errors)
        conditions = _bounded(scenario.changed_conditions, f"scenarios[{index}].changed_conditions", 20, errors, required=True)
        for condition_index, condition in enumerate(conditions):
            _text(condition, f"scenarios[{index}].changed_conditions[{condition_index}]", errors)
        if not isinstance(scenario.source, ScenarioSource):
            errors.append(f"scenarios[{index}].source must be a ScenarioSource")
        if scenario.severity is not None and not isinstance(scenario.severity, ScenarioSeverity):
            errors.append(f"scenarios[{index}].severity must be qualitative")
        scenario_keys.append(scenario.key)
    if len(scenario_keys) != len(set(scenario_keys)):
        errors.append("scenario keys must be unique")

    assumptions = _bounded(value.user_assumptions, "user_assumptions", MAX_USER_ASSUMPTIONS, errors)
    valid_scenarios = set(scenario_keys)
    for index, assumption in enumerate(assumptions):
        if not isinstance(assumption, UserSimulationAssumption):
            errors.append(f"user_assumptions[{index}] must be a UserSimulationAssumption")
            continue
        _text(assumption.statement, f"user_assumptions[{index}].statement", errors)
        if assumption.provenance is not FindingProvenance.USER_SUPPLIED:
            errors.append(f"user_assumptions[{index}].provenance must be USER_SUPPLIED")
        if assumption.scenario_key is not None and assumption.scenario_key not in valid_scenarios:
            errors.append(f"user_assumptions[{index}].scenario_key is unknown")

    if not evidence_ids and any(item.evidence_ref for item in value.success_measures):
        errors.append("success measure evidence references require evidence_refs")
    for index, measure in enumerate(measures):
        if not isinstance(measure, SuccessMeasure):
            errors.append(f"success_measures[{index}] must be a SuccessMeasure")
            continue
        _text(measure.condition, f"success_measures[{index}].condition", errors)
        if measure.evidence_ref is not None and measure.evidence_ref not in evidence_ids:
            errors.append(f"success_measures[{index}].evidence_ref is unknown")
    if errors:
        raise SimulationValidationError(errors)


def _findings(values: tuple[SimulationFinding, ...], name: str, evidence_ids: set[str], errors: list[str], *, required: bool = False) -> None:
    for index, finding in enumerate(_bounded(values, name, MAX_FINDINGS_PER_SECTION, errors, required=required)):
        if not isinstance(finding, SimulationFinding):
            errors.append(f"{name}[{index}] must be a SimulationFinding")
            continue
        _text(finding.statement, f"{name}[{index}].statement", errors)
        if not isinstance(finding.provenance, FindingProvenance):
            errors.append(f"{name}[{index}].provenance is invalid")
        if len(finding.evidence_refs) > MAX_SOURCE_ITEMS:
            errors.append(f"{name}[{index}].evidence_refs exceeds {MAX_SOURCE_ITEMS} items")
        for evidence_ref in finding.evidence_refs:
            if evidence_ref not in evidence_ids:
                errors.append(f"{name}[{index}].evidence_ref is unknown")


def validate_simulation_result(value: SimulationResultV1, source: SimulationInputV1 | None = None) -> None:
    if not isinstance(value, SimulationResultV1):
        raise SimulationValidationError(["value must be a SimulationResultV1"])
    errors: list[str] = []
    _metadata(value, errors)
    if not isinstance(value.confidence, ConfidenceLevel):
        errors.append("confidence must be qualitative")
    rationale = _bounded(value.confidence_rationale, "confidence_rationale", 20, errors, required=True)
    for index, item in enumerate(rationale):
        _text(item, f"confidence_rationale[{index}]", errors)
    evidence_ids = _evidence(value.evidence_refs, "evidence_refs", errors)

    results = _bounded(value.scenario_results, "scenario_results", MAX_SCENARIOS, errors, required=True)
    result_keys = []
    sections = (
        "elements_under_stress", "plausible_effects", "constraint_conflicts",
        "risk_observations", "mitigation_observations", "phase_sensitivities",
        "upside_conditions", "downside_conditions", "change_condition_triggers",
    )
    for index, result in enumerate(results):
        if not isinstance(result, StrategyStressResult):
            errors.append(f"scenario_results[{index}] must be a StrategyStressResult")
            continue
        _text(result.scenario_key, f"scenario_results[{index}].scenario_key", errors)
        if not isinstance(result.sensitivity, ScenarioSeverity):
            errors.append(f"scenario_results[{index}].sensitivity must be qualitative")
        for section in sections:
            _findings(
                getattr(result, section),
                f"scenario_results[{index}].{section}",
                evidence_ids,
                errors,
                required=section in {"elements_under_stress", "plausible_effects"},
            )
        result_keys.append(result.scenario_key)
    if len(result_keys) != len(set(result_keys)):
        errors.append("scenario result keys must be unique")

    _findings(value.cross_scenario_comparison, "cross_scenario_comparison", evidence_ids, errors, required=True)
    _findings(value.assumptions_used, "assumptions_used", evidence_ids, errors)
    _findings(value.uncertainties, "uncertainties", evidence_ids, errors, required=True)
    limitations = _bounded(value.limitations, "limitations", 20, errors, required=True)
    for index, limitation in enumerate(limitations):
        if not isinstance(limitation, SimulationLimitation):
            errors.append(f"limitations[{index}] must be a SimulationLimitation")
            continue
        _text(limitation.code, f"limitations[{index}].code", errors)
        _text(limitation.statement, f"limitations[{index}].statement", errors)
        if limitation.provenance is not FindingProvenance.SYSTEM:
            errors.append(f"limitations[{index}].provenance must be SYSTEM")

    if source is not None:
        try:
            validate_simulation_input(source)
        except SimulationValidationError as error:
            errors.extend(f"source.{item}" for item in error.errors)
        source_keys = {scenario.key for scenario in source.scenarios}
        if set(result_keys) != source_keys:
            errors.append("scenario_results must reference every source scenario exactly once")
        source_evidence = {item.evidence_id for item in source.evidence_refs}
        if not evidence_ids.issubset(source_evidence):
            errors.append("result evidence_refs must come from source evidence")
    if errors:
        raise SimulationValidationError(errors)
