"""Deterministic, provider-free quality validation for canonical strategies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re

from app.strategy.contracts import StrategyInput, StrategyResult
from app.strategy.validation import validate_strategy_input, validate_strategy_result


@dataclass(frozen=True)
class StrategyQualityIssue:
    code: str
    reason: str
    path: str


class StrategyQualityError(ValueError):
    def __init__(self, issues: list[StrategyQualityIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.code}: {issue.reason}" for issue in issues))


_EXPLICIT_TARGET = re.compile(r"(?:[$€£]\s*\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?%)")


def _normalize(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).split())


def _target_key(value: str) -> str:
    return re.sub(r"[$€£,\s]", "", value).casefold()


def _duplicates(values: list[str]) -> list[int]:
    seen: dict[str, int] = {}
    duplicates = []
    for index, value in enumerate(values):
        normalized = _normalize(value)
        if normalized in seen:
            duplicates.append(index)
        else:
            seen[normalized] = index
    return duplicates


def validate_strategy_quality(strategy_input: StrategyInput, strategy_result: StrategyResult) -> None:
    """Raise explainable issues for high-confidence Strategy quality failures."""

    validate_strategy_input(strategy_input)
    validate_strategy_result(strategy_result, strategy_input)
    issues: list[StrategyQualityIssue] = []

    if _normalize(strategy_result.approach) == _normalize(strategy_input.chosen_direction):
        issues.append(StrategyQualityIssue(
            "strategy.approach_restates_direction",
            "The approach only restates the chosen direction.",
            "approach",
        ))

    phase_content = [" ".join((
        phase.name, phase.purpose, *phase.focus_areas, phase.milestone_intent or "",
    )) for phase in strategy_result.phases]
    for index in _duplicates(phase_content):
        issues.append(StrategyQualityIssue(
            "strategy.duplicate_phase",
            "A strategic phase duplicates an earlier phase after normalization.",
            f"phases[{index}]",
        ))

    measures = [item.condition for item in strategy_result.success_measures]
    for index in _duplicates(measures):
        issues.append(StrategyQualityIssue(
            "strategy.duplicate_success_measure",
            "A success measure duplicates an earlier measure after normalization.",
            f"success_measures[{index}]",
        ))

    source_text = json.dumps(asdict(strategy_input), default=str, ensure_ascii=False)
    grounded_targets = {_target_key(item) for item in _EXPLICIT_TARGET.findall(source_text)}
    for index, measure in enumerate(measures):
        unsupported = sorted({item for item in _EXPLICIT_TARGET.findall(measure) if _target_key(item) not in grounded_targets})
        if unsupported:
            issues.append(StrategyQualityIssue(
                "strategy.unsupported_numeric_target",
                "A currency or percentage target is not grounded in StrategyInput.",
                f"success_measures[{index}]",
            ))

    if len(strategy_result.risks) != len(strategy_input.risks) or any(
        result.risk != source.risk
        for source, result in zip(strategy_input.risks, strategy_result.risks)
    ):
        issues.append(StrategyQualityIssue(
            "strategy.risk_preservation_violation",
            "Decision-derived risks must remain in their authoritative order.",
            "risks",
        ))

    source_assumptions = strategy_input.assumptions
    if strategy_result.assumptions[:len(source_assumptions)] != source_assumptions:
        issues.append(StrategyQualityIssue(
            "strategy.assumption_preservation_violation",
            "Authoritative assumptions must be preserved before generated assumptions.",
            "assumptions",
        ))
    generated_assumptions = strategy_result.assumptions[len(source_assumptions):]
    prior_assumptions = {_normalize(item.statement) for item in source_assumptions}
    for offset, assumption in enumerate(generated_assumptions, start=len(source_assumptions)):
        normalized = _normalize(assumption.statement)
        if assumption.source != "strategy_generation":
            issues.append(StrategyQualityIssue(
                "strategy.invalid_generated_assumption_source",
                "Generated assumptions must remain explicitly labeled as strategy generation.",
                f"assumptions[{offset}]",
            ))
        if normalized in prior_assumptions:
            issues.append(StrategyQualityIssue(
                "strategy.duplicate_generated_assumption",
                "A generated assumption duplicates an existing assumption.",
                f"assumptions[{offset}]",
            ))
        prior_assumptions.add(normalized)

    source_conditions = strategy_input.change_conditions
    if strategy_result.change_conditions[:len(source_conditions)] != source_conditions:
        issues.append(StrategyQualityIssue(
            "strategy.change_condition_preservation_violation",
            "Decision-derived change conditions must remain first and unchanged.",
            "change_conditions",
        ))
    prior_conditions = {_normalize(item) for item in source_conditions}
    for index, condition in enumerate(strategy_result.change_conditions[len(source_conditions):], start=len(source_conditions)):
        normalized = _normalize(condition)
        if normalized in prior_conditions:
            issues.append(StrategyQualityIssue(
                "strategy.duplicate_change_condition",
                "A generated change condition duplicates an existing condition.",
                f"change_conditions[{index}]",
            ))
        prior_conditions.add(normalized)

    if issues:
        raise StrategyQualityError(issues)
