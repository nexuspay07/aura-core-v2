"""Immutable, product-safe presentation contracts for Strategy Intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.strategy.contracts import ConfidenceLevel, StrategyResult


@dataclass(frozen=True)
class StrategyPhasePresentation:
    order: int
    name: str
    purpose: str
    focus_areas: tuple[str, ...]
    milestone_intent: str | None


@dataclass(frozen=True)
class StrategyRiskPresentation:
    risk: str
    mitigation: str | None


@dataclass(frozen=True)
class StrategySuccessMeasurePresentation:
    condition: str
    evidence_ref: str | None


@dataclass(frozen=True)
class StrategyAssumptionPresentation:
    statement: str
    source: str


@dataclass(frozen=True)
class StrategyEvidenceReferencePresentation:
    evidence_id: str
    citation_label: str | None


@dataclass(frozen=True)
class StrategyConstraintPresentation:
    statement: str


@dataclass(frozen=True)
class StrategyResourcePresentation:
    name: str
    description: str


@dataclass(frozen=True)
class StrategyPresentation:
    objective: str
    chosen_direction: str
    approach: str
    phases: tuple[StrategyPhasePresentation, ...]
    constraints: tuple[StrategyConstraintPresentation, ...]
    resources: tuple[StrategyResourcePresentation, ...]
    risks: tuple[StrategyRiskPresentation, ...]
    success_measures: tuple[StrategySuccessMeasurePresentation, ...]
    assumptions: tuple[StrategyAssumptionPresentation, ...]
    uncertainties: tuple[str, ...]
    change_conditions: tuple[str, ...]
    confidence: ConfidenceLevel
    confidence_rationale: tuple[str, ...]
    time_horizon: str | None
    evidence_references: tuple[StrategyEvidenceReferencePresentation, ...]
    source_decision_id: int | None
    source_reference: str | None


def to_strategy_presentation(strategy_result: StrategyResult) -> StrategyPresentation:
    """Project an authorized canonical result without inference or rewriting."""

    return StrategyPresentation(
        objective=strategy_result.objective,
        chosen_direction=strategy_result.chosen_direction,
        approach=strategy_result.approach,
        phases=tuple(
            StrategyPhasePresentation(
                order=phase.order,
                name=phase.name,
                purpose=phase.purpose,
                focus_areas=phase.focus_areas,
                milestone_intent=phase.milestone_intent,
            )
            for phase in strategy_result.phases
        ),
        constraints=tuple(
            StrategyConstraintPresentation(statement=item.statement)
            for item in strategy_result.constraints
        ),
        resources=tuple(
            StrategyResourcePresentation(name=item.name, description=item.description)
            for item in strategy_result.resources
        ),
        risks=tuple(
            StrategyRiskPresentation(risk=item.risk, mitigation=item.mitigation)
            for item in strategy_result.risks
        ),
        success_measures=tuple(
            StrategySuccessMeasurePresentation(
                condition=item.condition,
                evidence_ref=item.evidence_ref,
            )
            for item in strategy_result.success_measures
        ),
        assumptions=tuple(
            StrategyAssumptionPresentation(statement=item.statement, source=item.source)
            for item in strategy_result.assumptions
        ),
        uncertainties=strategy_result.uncertainties,
        change_conditions=strategy_result.change_conditions,
        confidence=strategy_result.confidence,
        confidence_rationale=strategy_result.confidence_rationale,
        time_horizon=strategy_result.time_horizon,
        evidence_references=tuple(
            StrategyEvidenceReferencePresentation(
                evidence_id=item.evidence_id,
                citation_label=item.citation_label,
            )
            for item in strategy_result.evidence_refs
        ),
        source_decision_id=strategy_result.source_decision_id,
        source_reference=strategy_result.source_reference,
    )
