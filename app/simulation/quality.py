"""Deterministic trust validation for canonical Simulation V1 results."""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.simulation.contracts import (
    FindingProvenance,
    SimulationExecutionInputV1,
    SimulationFinding,
    SimulationResultV1,
)
from app.simulation.validation import (
    validate_simulation_execution_input,
    validate_simulation_result,
)


NON_FORECAST_LIMITATION_CODE = "not_calibrated"


@dataclass(frozen=True)
class SimulationQualityIssue:
    code: str
    reason: str
    path: str


class SimulationQualityError(ValueError):
    def __init__(self, issues: list[SimulationQualityIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.code}: {issue.reason}" for issue in issues))


_NUMERIC_PROBABILITY = (
    re.compile(r"\b\d+(?:\.\d+)?\s*%\s*(?:chance|probability|likelihood)\b", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s+percent\s+(?:chance|probability|likelihood)\b", re.I),
    re.compile(r"\b(?:chance|probability|likelihood)\s*(?:of|is|:)?\s*\d+(?:\.\d+)?\s*%", re.I),
    re.compile(r"\bprobability\s*(?:of|is|:)?\s*(?:0(?:\.\d+)?|1(?:\.0+)?)\b", re.I),
    re.compile(r"\b(?:success|failure)\s+probability\b", re.I),
)
_FORECAST_CLAIM = (
    re.compile(r"\bthe model predicts\b", re.I),
    re.compile(r"\bexpected return\s+will be\s+[$€£]", re.I),
)
_OVERCONFIDENT = re.compile(
    r"\b(?:guaranteed to succeed|guaranteed outcome|will definitely succeed|certain to happen)\b",
    re.I,
)
_SCENARIO_SECTIONS = (
    "elements_under_stress", "plausible_effects", "constraint_conflicts",
    "risk_observations", "mitigation_observations", "phase_sensitivities",
    "upside_conditions", "downside_conditions", "change_condition_triggers",
)


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _issue(issues: list[SimulationQualityIssue], code: str, reason: str, path: str) -> None:
    issues.append(SimulationQualityIssue(code, reason, path))


def _finding_collections(result: SimulationResultV1):
    for result_index, scenario_result in enumerate(result.scenario_results):
        for section in _SCENARIO_SECTIONS:
            yield f"scenario_results[{result_index}].{section}", getattr(scenario_result, section)
    yield "cross_scenario_comparison", result.cross_scenario_comparison
    yield "assumptions_used", result.assumptions_used
    yield "uncertainties", result.uncertainties


def _source_material(source) -> set[str]:
    values = {
        source.objective, source.chosen_direction, source.strategic_approach,
        *(phase.name for phase in source.phases),
        *(f"phase {phase.order}" for phase in source.phases),
        *(str(phase.order) for phase in source.phases),
        *(phase.purpose for phase in source.phases),
        *(item for phase in source.phases for item in phase.focus_areas),
        *(phase.milestone_intent for phase in source.phases if phase.milestone_intent),
        *(item.condition for item in source.success_measures),
        *(item.constraint_id for item in source.constraints),
        *(item.statement for item in source.constraints),
        *(item.name for item in source.resources),
        *(item.description for item in source.resources),
        *(item.risk for item in source.risks),
        *(item.mitigation for item in source.risks if item.mitigation),
        *(item.statement for item in source.strategy_assumptions),
        *source.uncertainties,
        *source.change_conditions,
    }
    return {_normalize(item) for item in values}


def _check_duplicates(result: SimulationResultV1, issues: list[SimulationQualityIssue]) -> None:
    for path, findings in _finding_collections(result):
        seen: set[str] = set()
        for index, finding in enumerate(findings):
            normalized = _normalize(finding.statement)
            if normalized in seen:
                _issue(
                    issues, "simulation.duplicate_finding",
                    "A finding duplicates an earlier finding in the same collection.",
                    f"{path}[{index}]",
                )
            seen.add(normalized)


def _check_predictive_claims(result: SimulationResultV1, issues: list[SimulationQualityIssue]) -> None:
    texts = [
        (f"{path}[{index}].statement", finding.statement)
        for path, findings in _finding_collections(result)
        for index, finding in enumerate(findings)
        if finding.provenance in {FindingProvenance.MODEL_GENERATED, FindingProvenance.DERIVED}
    ]
    texts.extend(
        (f"confidence_rationale[{index}]", text)
        for index, text in enumerate(result.confidence_rationale)
    )
    for path, text in texts:
        if any(pattern.search(text) for pattern in _NUMERIC_PROBABILITY):
            _issue(
                issues, "simulation.numeric_probability",
                "Simulation V1 cannot assert numerical predictive probability.", path,
            )
        if any(pattern.search(text) for pattern in _FORECAST_CLAIM):
            _issue(
                issues, "simulation.forecast_claim",
                "Simulation V1 cannot assert a calibrated forecast.", path,
            )
        if _OVERCONFIDENT.search(text):
            _issue(
                issues, "simulation.predictive_certainty",
                "Simulation V1 cannot assert predictive certainty.", path,
            )


def _check_provenance(execution_input, result, issues):
    source = execution_input.simulation_input
    source_material = _source_material(source)
    user_material = {_normalize(item.statement) for item in source.user_assumptions}
    strategy_assumptions = {_normalize(item.statement) for item in source.strategy_assumptions}
    phases = {
        *(_normalize(item.name) for item in source.phases),
        *(f"phase {item.order}" for item in source.phases),
        *(str(item.order) for item in source.phases),
    }
    constraints = {
        *(_normalize(item.constraint_id) for item in source.constraints),
        *(_normalize(item.statement) for item in source.constraints),
    }
    change_conditions = {_normalize(item) for item in source.change_conditions}

    for path, findings in _finding_collections(result):
        for index, finding in enumerate(findings):
            item_path = f"{path}[{index}]"
            normalized = _normalize(finding.statement)
            if finding.provenance is FindingProvenance.SOURCE and normalized not in source_material:
                _issue(
                    issues, "simulation.invalid_finding_provenance",
                    "A SOURCE finding does not identify trusted Strategy material.", item_path,
                )
            elif finding.provenance is FindingProvenance.USER_SUPPLIED and normalized not in user_material:
                _issue(
                    issues, "simulation.invalid_finding_provenance",
                    "A USER_SUPPLIED finding does not identify an explicit user assumption.", item_path,
                )
            elif finding.provenance is FindingProvenance.SYSTEM:
                _issue(
                    issues, "simulation.invalid_finding_provenance",
                    "Analytical findings cannot claim SYSTEM provenance.", item_path,
                )

    for scenario_index, scenario_result in enumerate(result.scenario_results):
        for index, finding in enumerate(scenario_result.phase_sensitivities):
            if finding.provenance is FindingProvenance.SOURCE and _normalize(finding.statement) not in phases:
                _issue(
                    issues, "simulation.phase_reference",
                    "A source phase reference does not exist in the exact Strategy revision.",
                    f"scenario_results[{scenario_index}].phase_sensitivities[{index}]",
                )
        for index, finding in enumerate(scenario_result.constraint_conflicts):
            if finding.provenance is FindingProvenance.SOURCE and _normalize(finding.statement) not in constraints:
                _issue(
                    issues, "simulation.constraint_reference",
                    "A source constraint reference does not exist in the exact Strategy revision.",
                    f"scenario_results[{scenario_index}].constraint_conflicts[{index}]",
                )
        for index, finding in enumerate(scenario_result.change_condition_triggers):
            if finding.provenance is FindingProvenance.SOURCE and _normalize(finding.statement) not in change_conditions:
                _issue(
                    issues, "simulation.change_condition_reference",
                    "A source change-condition reference does not exist in the exact Strategy revision.",
                    f"scenario_results[{scenario_index}].change_condition_triggers[{index}]",
                )

    for index, finding in enumerate(result.assumptions_used):
        normalized = _normalize(finding.statement)
        valid = (
            finding.provenance is FindingProvenance.SOURCE and normalized in strategy_assumptions
        ) or (
            finding.provenance is FindingProvenance.USER_SUPPLIED and normalized in user_material
        ) or finding.provenance in {FindingProvenance.MODEL_GENERATED, FindingProvenance.DERIVED}
        if not valid:
            _issue(
                issues, "simulation.assumption_provenance",
                "An assumption does not match its declared provenance.",
                f"assumptions_used[{index}]",
            )


def _check_scenario_quality(execution_input, result, issues):
    scenarios = execution_input.simulation_input.scenarios
    requested = {item.key for item in scenarios}
    returned = [item.scenario_key for item in result.scenario_results]
    if len(returned) != len(set(returned)) or set(returned) != requested:
        _issue(
            issues, "simulation.scenario_coverage",
            "Scenario results must cover every requested scenario exactly once.",
            "scenario_results",
        )

    materially_different = len({
        tuple(_normalize(item) for item in scenario.changed_conditions)
        for scenario in scenarios
    }) > 1
    if len(result.scenario_results) > 1 and materially_different:
        for section in ("elements_under_stress", "plausible_effects"):
            collections = [
                tuple(_normalize(item.statement) for item in getattr(value, section))
                for value in result.scenario_results
            ]
            if len(set(collections)) == 1:
                _issue(
                    issues, "simulation.scenario_repetition",
                    "Materially different scenarios repeat the same core analysis.",
                    f"scenario_results.*.{section}",
                )

    if len(scenarios) > 1:
        comparison = {_normalize(item.statement) for item in result.cross_scenario_comparison}
        scenario_only = {
            *(_normalize(item.name) for item in scenarios),
            *(_normalize(item.description) for item in scenarios),
            *(_normalize(condition) for item in scenarios for condition in item.changed_conditions),
        }
        if not comparison or comparison.issubset(scenario_only):
            _issue(
                issues, "simulation.cross_scenario_comparison",
                "Multiple scenarios require a distinct cross-scenario comparison.",
                "cross_scenario_comparison",
            )


def validate_simulation_result_quality(
    execution_input: SimulationExecutionInputV1,
    result: SimulationResultV1,
) -> None:
    """Reject high-confidence cross-object trust violations without mutation."""

    validate_simulation_execution_input(execution_input)
    validate_simulation_result(result)
    issues: list[SimulationQualityIssue] = []
    source = execution_input.simulation_input

    if result.simulation_type is not source.simulation_type or result.schema_version != source.schema_version:
        _issue(
            issues, "simulation.execution_identity",
            "Result type and schema must match the execution input.", "simulation_type",
        )

    _check_scenario_quality(execution_input, result, issues)

    source_evidence = {item.evidence_id for item in source.evidence_refs}
    if any(item.evidence_id not in source_evidence for item in result.evidence_refs):
        _issue(
            issues, "simulation.unsupported_evidence",
            "Result evidence must come from the exact Strategy revision.", "evidence_refs",
        )

    _check_provenance(execution_input, result, issues)
    _check_predictive_claims(result, issues)
    _check_duplicates(result, issues)

    if NON_FORECAST_LIMITATION_CODE not in {item.code for item in result.limitations}:
        _issue(
            issues, "simulation.missing_non_forecast_limitation",
            "Simulation V1 requires its canonical non-forecast limitation.", "limitations",
        )

    if issues:
        raise SimulationQualityError(issues)
