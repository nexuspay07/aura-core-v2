"""Provider-independent orchestration for canonical Simulation V1."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ModelProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    analysis_timeout_seconds,
    configured_model_provider,
)
from app.simulation.contracts import (
    FindingProvenance,
    SimulationExecutionInputV1,
    SimulationFinding,
    SimulationLimitation,
    SimulationResultV1,
    ScenarioSeverity,
    StrategyStressResult,
)
from app.simulation.model_schema import SIMULATION_SCHEMA_NAME, simulation_model_schema
from app.simulation.prompts import SIMULATION_SYSTEM_PROMPT, simulation_repair_instruction
from app.simulation.quality import (
    NON_FORECAST_LIMITATION_CODE,
    SimulationQualityError,
    validate_simulation_result_quality,
)
from app.simulation.validation import (
    SimulationValidationError,
    validate_simulation_execution_input,
    validate_simulation_result,
)
from app.strategy.contracts import ConfidenceLevel


class SimulationGenerationError(ValueError):
    """Provider output could not be assembled into canonical Simulation V1."""

    def __init__(self, message: str, code: str = "simulation_generation.invalid_output"):
        self.code = code
        super().__init__(message)


_OUTPUT_FIELDS = {
    "scenario_results", "cross_scenario_comparison", "assumptions_used",
    "uncertainties", "confidence", "confidence_rationale", "evidence_refs",
}
_FINDING_SECTIONS = (
    "elements_under_stress", "plausible_effects", "constraint_conflicts",
    "risk_observations", "mitigation_observations", "phase_sensitivities",
    "upside_conditions", "downside_conditions", "change_condition_triggers",
)
_SCENARIO_FIELDS = {
    "scenario_key", "sensitivity",
    *_FINDING_SECTIONS,
}
_FINDING_FIELDS = {"statement", "provenance", "evidence_refs"}


def _text(value: object, code: str = "simulation_generation.empty_text") -> str:
    if not isinstance(value, str) or not value.strip():
        raise SimulationGenerationError("provider text must be meaningful", code)
    return value.strip()


def _array(value: object, code: str) -> list:
    if not isinstance(value, list):
        raise SimulationGenerationError("provider field must be an array", code)
    return value


def _repair_details(error: Exception) -> tuple[str, tuple[str, ...]]:
    if isinstance(error, SimulationQualityError):
        return "quality_validation", tuple(sorted({item.code for item in error.issues}))
    if isinstance(error, SimulationGenerationError):
        return "generation_validation", (error.code,)
    if isinstance(error, SimulationValidationError):
        return "structural_validation", ("simulation_generation.structural_validation",)
    if isinstance(error, InvalidModelResponseError):
        return "provider_response", ("simulation_generation.provider_response",)
    return "generation_failure", ("simulation_generation.invalid_output",)


class SimulationOrchestrator:
    """Generate and validate one Strategy Stress Test without persistence."""

    max_provider_calls = 2

    def __init__(self, provider: ModelProvider | None = None):
        self.provider = provider or configured_model_provider()

    @staticmethod
    def payload(execution_input: SimulationExecutionInputV1) -> dict[str, Any]:
        source = execution_input.simulation_input
        return {
            "objective": source.objective,
            "chosen_direction": source.chosen_direction,
            "strategic_approach": source.strategic_approach,
            "phases": [asdict(item) for item in source.phases],
            "success_measures": [asdict(item) for item in source.success_measures],
            "scenarios": [asdict(item) for item in source.scenarios],
            "constraints": [asdict(item) for item in source.constraints],
            "resources": [asdict(item) for item in source.resources],
            "risks": [asdict(item) for item in source.risks],
            "strategy_assumptions": [asdict(item) for item in source.strategy_assumptions],
            "user_assumptions": [asdict(item) for item in source.user_assumptions],
            "uncertainties": list(source.uncertainties),
            "change_conditions": list(source.change_conditions),
            "time_horizon": source.time_horizon,
            "evidence_refs": [asdict(item) for item in source.evidence_refs],
        }

    def run(self, execution_input: SimulationExecutionInputV1) -> SimulationResultV1:
        validate_simulation_execution_input(execution_input)
        source = execution_input.simulation_input
        payload = self.payload(execution_input)
        schema = simulation_model_schema(
            (item.key for item in source.scenarios),
            (item.evidence_id for item in source.evidence_refs),
        )
        repair = ""
        for attempt in range(self.max_provider_calls):
            try:
                raw, _usage = self.provider.generate_structured(
                    system=SIMULATION_SYSTEM_PROMPT + repair,
                    payload=payload,
                    timeout_seconds=analysis_timeout_seconds(),
                    reasoning_effort="medium" if attempt == 0 else "low",
                    output_schema=schema,
                    schema_name=SIMULATION_SCHEMA_NAME,
                )
                result = self._result(execution_input, raw)
                validate_simulation_result(result, source)
                validate_simulation_result_quality(execution_input, result)
                return result
            except (
                InvalidModelResponseError,
                SimulationGenerationError,
                SimulationValidationError,
                SimulationQualityError,
            ) as error:
                if attempt + 1 == self.max_provider_calls:
                    raise
                category, codes = _repair_details(error)
                repair = simulation_repair_instruction(category=category, codes=codes)
            except (ProviderTimeoutError, ProviderUnavailableError):
                raise
        raise SimulationGenerationError(
            "simulation generation exhausted", "simulation_generation.exhausted",
        )

    def _result(self, execution_input: SimulationExecutionInputV1, raw: object) -> SimulationResultV1:
        if not isinstance(raw, dict):
            raise SimulationGenerationError(
                "provider output must be an object", "simulation_generation.invalid_output_type",
            )
        if set(raw) - _OUTPUT_FIELDS:
            raise SimulationGenerationError(
                "provider output contains unexpected fields", "simulation_generation.unexpected_fields",
            )
        if _OUTPUT_FIELDS - set(raw):
            raise SimulationGenerationError(
                "provider output is missing required fields", "simulation_generation.missing_fields",
            )

        scenario_results = self._scenario_results(raw["scenario_results"])
        comparison = self._findings(raw["cross_scenario_comparison"])
        assumptions = self._findings(raw["assumptions_used"])
        uncertainties = self._findings(raw["uncertainties"])
        rationale = tuple(
            _text(item) for item in _array(
                raw["confidence_rationale"], "simulation_generation.invalid_text_collection",
            )
        )
        try:
            confidence = ConfidenceLevel(raw["confidence"])
        except (ValueError, TypeError) as error:
            raise SimulationGenerationError(
                "confidence must be qualitative", "simulation_generation.invalid_confidence",
            ) from error

        evidence_values = _array(
            raw["evidence_refs"], "simulation_generation.invalid_evidence_collection",
        )
        if any(not isinstance(item, str) for item in evidence_values):
            raise SimulationGenerationError(
                "evidence references must be strings", "simulation_generation.invalid_evidence_reference",
            )
        if len(evidence_values) != len(set(evidence_values)):
            raise SimulationGenerationError(
                "evidence references must be unique", "simulation_generation.invalid_evidence_reference",
            )
        source_evidence = {
            item.evidence_id: item for item in execution_input.simulation_input.evidence_refs
        }
        try:
            evidence = tuple(source_evidence[item] for item in evidence_values)
        except KeyError as error:
            raise SimulationGenerationError(
                "evidence reference is not available", "simulation_generation.invalid_evidence_reference",
            ) from error

        return SimulationResultV1(
            scenario_results=scenario_results,
            cross_scenario_comparison=comparison,
            assumptions_used=assumptions,
            uncertainties=uncertainties,
            limitations=(SimulationLimitation(
                NON_FORECAST_LIMITATION_CODE,
                "This Strategy Stress Test is scenario analysis and is not a calibrated real-world forecast.",
            ),),
            confidence=confidence,
            confidence_rationale=rationale,
            evidence_refs=evidence,
        )

    def _scenario_results(self, value: object) -> tuple[StrategyStressResult, ...]:
        values = _array(value, "simulation_generation.invalid_scenario_collection")
        results = []
        for item in values:
            if not isinstance(item, dict) or set(item) != _SCENARIO_FIELDS:
                raise SimulationGenerationError(
                    "scenario result has an invalid structure",
                    "simulation_generation.invalid_scenario_structure",
                )
            try:
                sensitivity = ScenarioSeverity(item["sensitivity"])
            except (ValueError, TypeError) as error:
                raise SimulationGenerationError(
                    "scenario sensitivity must be qualitative",
                    "simulation_generation.invalid_sensitivity",
                ) from error
            results.append(StrategyStressResult(
                scenario_key=_text(
                    item["scenario_key"], "simulation_generation.invalid_scenario_reference",
                ),
                sensitivity=sensitivity,
                **{name: self._findings(item[name]) for name in _FINDING_SECTIONS},
            ))
        return tuple(results)

    @staticmethod
    def _findings(value: object) -> tuple[SimulationFinding, ...]:
        values = _array(value, "simulation_generation.invalid_finding_collection")
        findings = []
        for item in values:
            if not isinstance(item, dict) or set(item) != _FINDING_FIELDS:
                raise SimulationGenerationError(
                    "finding has an invalid structure",
                    "simulation_generation.invalid_finding_structure",
                )
            try:
                provenance = FindingProvenance(item["provenance"])
            except (ValueError, TypeError) as error:
                raise SimulationGenerationError(
                    "finding provenance is invalid",
                    "simulation_generation.invalid_finding_provenance",
                ) from error
            if provenance is FindingProvenance.SYSTEM:
                raise SimulationGenerationError(
                    "provider cannot assign system provenance",
                    "simulation_generation.invalid_finding_provenance",
                )
            evidence = _array(
                item["evidence_refs"], "simulation_generation.invalid_evidence_collection",
            )
            if any(not isinstance(reference, str) for reference in evidence):
                raise SimulationGenerationError(
                    "finding evidence references must be strings",
                    "simulation_generation.invalid_evidence_reference",
                )
            findings.append(SimulationFinding(
                statement=_text(item["statement"]),
                provenance=provenance,
                evidence_refs=tuple(evidence),
            ))
        return tuple(findings)


simulation_orchestrator = SimulationOrchestrator()
