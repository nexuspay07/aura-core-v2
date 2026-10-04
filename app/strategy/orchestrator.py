"""Canonical, product-independent Strategy Intelligence orchestration."""

from __future__ import annotations

from dataclasses import asdict
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ModelProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    analysis_timeout_seconds,
    configured_model_provider,
)
from app.strategy.contracts import (
    StrategyAssumption,
    StrategyInput,
    StrategyPhase,
    StrategyResult,
    StrategyRisk,
    SuccessMeasure,
)
from app.strategy.model_schema import STRATEGY_SCHEMA_NAME, strategy_model_schema
from app.strategy.prompts import STRATEGY_RETRY_PROMPT, STRATEGY_SYSTEM_PROMPT
from app.strategy.quality import StrategyQualityError, validate_strategy_quality
from app.strategy.validation import StrategyValidationError, validate_strategy_input, validate_strategy_result


class StrategyGenerationError(ValueError):
    """The provider response could not form a valid canonical strategy."""

    def __init__(self, message: str, code: str = "strategy_generation.invalid_output"):
        self.code = code
        super().__init__(message)


logger = logging.getLogger("uvicorn.error")


_OUTPUT_FIELDS = {
    "approach", "phases", "risk_mitigations", "success_measures",
    "assumptions", "uncertainties", "change_conditions",
}
_NUMBER_PATTERN = re.compile(r"\b\d[\d,]*(?:\.\d+)?%?")


def _failure_diagnostics(error: Exception) -> tuple[str, str, str]:
    if isinstance(error, StrategyQualityError):
        codes = ",".join(sorted({issue.code for issue in error.issues})) or "none"
        return "quality_validation", codes, "none"
    if isinstance(error, StrategyValidationError):
        return "structural_validation", "none", "none"
    if isinstance(error, StrategyGenerationError):
        return "generation_validation", "none", error.code
    if isinstance(error, InvalidModelResponseError):
        return "provider_response", "none", "none"
    if isinstance(error, ProviderTimeoutError):
        return "provider_timeout", "none", "none"
    if isinstance(error, ProviderUnavailableError):
        return "provider_unavailable", "none", "none"
    return "unknown", "none", "none"


def _log_attempt_failure(error: Exception, *, attempt: int, max_attempts: int, retryable: bool) -> None:
    category, quality_codes, generation_codes = _failure_diagnostics(error)
    repair_next = retryable and attempt < max_attempts
    terminal = not repair_next
    logger.warning(
        "strategy_generation_stage=%s attempt=%s max_attempts=%s category=%s "
        "quality_codes=%s generation_codes=%s repair_next=%s repair_exhausted=%s provider_calls=%s",
        "terminal_failure" if terminal else "attempt_failed",
        attempt,
        max_attempts,
        category,
        quality_codes,
        generation_codes,
        str(repair_next).lower(),
        str(terminal and attempt == max_attempts).lower(),
        attempt,
    )


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyGenerationError(f"{name} must be meaningful", "strategy_generation.empty_text")
    return value.strip()


def _string_list(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise StrategyGenerationError(f"{name} must be an array", "strategy_generation.invalid_array")
    return tuple(_text(item, f"{name} item") for item in value)


class StrategyOrchestrator:
    """Generate Strategy content while preserving all trusted input metadata."""

    max_provider_calls = 2

    def __init__(self, provider: ModelProvider | None = None):
        self.provider = provider or configured_model_provider()

    @staticmethod
    def payload(strategy_input: StrategyInput) -> dict[str, Any]:
        """Return bounded descriptive input without tenant or provenance IDs."""

        return {
            "objective": strategy_input.objective,
            "chosen_direction": strategy_input.chosen_direction,
            "constraints": [item.statement for item in strategy_input.constraints],
            "resources": [asdict(item) for item in strategy_input.resources],
            "assumptions": [item.statement for item in strategy_input.assumptions],
            "risks": [item.risk for item in strategy_input.risks],
            "uncertainties": list(strategy_input.uncertainties),
            "time_horizon": strategy_input.time_horizon,
            "change_conditions": list(strategy_input.change_conditions),
            "alternatives": [item.approach for item in strategy_input.considered_alternatives],
            "confidence": strategy_input.confidence.value,
            "confidence_rationale": list(strategy_input.confidence_rationale),
        }

    def generate(
        self,
        strategy_input: StrategyInput,
        *,
        before_provider_attempt: Callable[[], None] | None = None,
    ) -> StrategyResult:
        validate_strategy_input(strategy_input)
        payload = self.payload(strategy_input)
        last_error: Exception | None = None
        for attempt in range(self.max_provider_calls):
            if before_provider_attempt is not None:
                before_provider_attempt()
            attempt_number = attempt + 1
            logger.warning(
                "strategy_generation_stage=attempt_started attempt=%s max_attempts=%s "
                "repair_attempt=%s provider_calls=%s",
                attempt_number,
                self.max_provider_calls,
                str(attempt_number > 1).lower(),
                attempt_number,
            )
            try:
                raw, _usage = self.provider.generate_structured(
                    system=STRATEGY_SYSTEM_PROMPT + (STRATEGY_RETRY_PROMPT if attempt else ""),
                    payload=payload,
                    timeout_seconds=analysis_timeout_seconds(),
                    reasoning_effort="medium" if attempt == 0 else "low",
                    output_schema=strategy_model_schema(),
                    schema_name=STRATEGY_SCHEMA_NAME,
                )
                result = self._result(strategy_input, raw)
                validate_strategy_result(result, strategy_input)
                validate_strategy_quality(strategy_input, result)
                logger.warning(
                    "strategy_generation_stage=attempt_succeeded attempt=%s max_attempts=%s "
                    "repair_attempt=%s provider_calls=%s",
                    attempt_number,
                    self.max_provider_calls,
                    str(attempt_number > 1).lower(),
                    attempt_number,
                )
                return result
            except (
                InvalidModelResponseError,
                StrategyGenerationError,
                StrategyQualityError,
                StrategyValidationError,
            ) as error:
                last_error = error
                _log_attempt_failure(
                    error,
                    attempt=attempt_number,
                    max_attempts=self.max_provider_calls,
                    retryable=True,
                )
                if attempt + 1 == self.max_provider_calls:
                    raise
            except (ProviderTimeoutError, ProviderUnavailableError) as error:
                _log_attempt_failure(
                    error,
                    attempt=attempt_number,
                    max_attempts=self.max_provider_calls,
                    retryable=False,
                )
                raise
        raise StrategyGenerationError("strategy generation failed", "strategy_generation.exhausted") from last_error

    def _result(self, source: StrategyInput, raw: object) -> StrategyResult:
        if not isinstance(raw, dict):
            raise StrategyGenerationError("provider output must be an object", "strategy_generation.invalid_output_type")
        unexpected = set(raw) - _OUTPUT_FIELDS
        missing = _OUTPUT_FIELDS - set(raw)
        if unexpected:
            raise StrategyGenerationError(f"provider output contains forbidden fields: {', '.join(sorted(unexpected))}", "strategy_generation.unexpected_fields")
        if missing:
            raise StrategyGenerationError(f"provider output is missing fields: {', '.join(sorted(missing))}", "strategy_generation.missing_fields")

        approach = _text(raw["approach"], "approach")
        if approach.casefold() == source.chosen_direction.strip().casefold():
            raise StrategyGenerationError("approach must develop rather than repeat chosen_direction", "strategy_generation.repeated_direction")
        phases = self._phases(raw["phases"])
        success = tuple(SuccessMeasure(item) for item in _string_list(raw["success_measures"], "success_measures"))
        if not success:
            raise StrategyGenerationError("at least one success measure is required", "strategy_generation.missing_success_measure")
        generated_assumptions = tuple(
            StrategyAssumption(item, "strategy_generation")
            for item in _string_list(raw["assumptions"], "assumptions")
        )
        generated_uncertainties = _string_list(raw["uncertainties"], "uncertainties")
        generated_changes = _string_list(raw["change_conditions"], "change_conditions")
        risks = self._risks(source, raw["risk_mitigations"])
        self._validate_generated_numbers(source, approach, phases, success, generated_assumptions,
                                         generated_uncertainties, generated_changes, risks)

        return StrategyResult(
            scope=source.scope,
            source_decision_id=source.source_decision_id,
            source_reference=source.source_reference,
            objective=source.objective,
            chosen_direction=source.chosen_direction,
            approach=approach,
            constraints=source.constraints,
            assumptions=source.assumptions + generated_assumptions,
            phases=phases,
            resources=source.resources,
            risks=risks,
            success_measures=success,
            alternatives=source.considered_alternatives,
            uncertainties=source.uncertainties + generated_uncertainties,
            change_conditions=source.change_conditions + generated_changes,
            evidence_refs=source.evidence_refs,
            confidence=source.confidence,
            confidence_rationale=source.confidence_rationale,
            time_horizon=source.time_horizon,
        )

    @staticmethod
    def _phases(value: object) -> tuple[StrategyPhase, ...]:
        if not isinstance(value, list) or not value:
            raise StrategyGenerationError("phases must be a non-empty array", "strategy_generation.invalid_phase_collection")
        phases = []
        expected = {"order", "name", "purpose", "focus_areas", "milestone_intent"}
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict) or set(item) != expected:
                raise StrategyGenerationError(f"phase {index} has an invalid structure", "strategy_generation.invalid_phase_structure")
            order = item["order"]
            if not isinstance(order, int) or isinstance(order, bool):
                raise StrategyGenerationError(f"phase {index} order must be an integer", "strategy_generation.invalid_phase_order")
            milestone = item["milestone_intent"]
            if milestone is not None:
                milestone = _text(milestone, f"phase {index} milestone_intent")
            phases.append(StrategyPhase(
                order=order,
                name=_text(item["name"], f"phase {index} name"),
                purpose=_text(item["purpose"], f"phase {index} purpose"),
                focus_areas=_string_list(item["focus_areas"], f"phase {index} focus_areas"),
                milestone_intent=milestone,
            ))
        if [item.order for item in phases] != list(range(1, len(phases) + 1)):
            raise StrategyGenerationError("phase order must be contiguous and begin at 1", "strategy_generation.invalid_phase_sequence")
        return tuple(phases)

    @staticmethod
    def _risks(source: StrategyInput, value: object) -> tuple[StrategyRisk, ...]:
        if not isinstance(value, list):
            raise StrategyGenerationError("risk_mitigations must be an array", "strategy_generation.invalid_risk_collection")
        mitigations: dict[int, str] = {}
        for item in value:
            if not isinstance(item, dict) or set(item) != {"risk_index", "mitigation"}:
                raise StrategyGenerationError("risk mitigation has an invalid structure", "strategy_generation.invalid_risk_structure")
            index = item["risk_index"]
            if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(source.risks):
                raise StrategyGenerationError("risk mitigation references an unknown risk", "strategy_generation.invalid_risk_reference")
            if index in mitigations:
                raise StrategyGenerationError("risk mitigation index must be unique", "strategy_generation.duplicate_risk_reference")
            mitigations[index] = _text(item["mitigation"], "risk mitigation")
        return tuple(StrategyRisk(item.risk, mitigations.get(index, item.mitigation)) for index, item in enumerate(source.risks))

    @staticmethod
    def _validate_generated_numbers(source: StrategyInput, *values: object) -> None:
        source_text = json.dumps(StrategyOrchestrator.payload(source), default=str, ensure_ascii=False)
        allowed = {item.replace(",", "") for item in _NUMBER_PATTERN.findall(source_text)}
        generated_strings: list[str] = []
        def collect(value: object) -> None:
            if isinstance(value, str): generated_strings.append(value)
            elif isinstance(value, dict):
                for item in value.values(): collect(item)
            elif isinstance(value, (list, tuple)):
                for item in value: collect(item)
            elif hasattr(value, "__dataclass_fields__"):
                collect(asdict(value))
        collect(values)
        generated_text = " ".join(generated_strings)
        invented = sorted({item for item in _NUMBER_PATTERN.findall(generated_text) if item.replace(",", "") not in allowed})
        if invented:
            raise StrategyGenerationError(f"generated strategy contains unsupported numeric values: {', '.join(invented)}", "strategy_generation.unsupported_numeric_value")


strategy_orchestrator = StrategyOrchestrator()
