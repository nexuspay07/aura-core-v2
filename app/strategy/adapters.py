"""Deterministic reconciliation from completed Decision V2 into Strategy."""

from __future__ import annotations

from collections.abc import Mapping

from app.intelligence_v2.contracts import AnalysisExecution, DecisionState
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAlternative,
    StrategyAssumption,
    StrategyConstraint,
    StrategyInput,
    StrategyResource,
    StrategyRisk,
    StrategyScope,
)
from app.strategy.validation import StrategyValidationError, validate_strategy_input


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyValidationError([f"{field_name} must be meaningful"])
    return value.strip()


def _resources(state: DecisionState) -> tuple[StrategyResource, ...]:
    phase2 = state.analysis_outputs.get("phase2", {})
    if not isinstance(phase2, Mapping):
        raise StrategyValidationError(["Decision V2 phase2 output must be structured"])
    raw_resources = phase2.get("resources", [])
    if not isinstance(raw_resources, (list, tuple)):
        raise StrategyValidationError(["Decision V2 resources must be an ordered collection"])
    resources = []
    for index, item in enumerate(raw_resources, start=1):
        if not isinstance(item, Mapping):
            raise StrategyValidationError([f"Decision V2 resource {index} must be structured"])
        resources.append(StrategyResource(
            name=_text(item.get("type"), f"Decision V2 resource {index} type"),
            description=_text(item.get("value"), f"Decision V2 resource {index} value"),
        ))
    return tuple(resources)


def _uncertainties(state: DecisionState) -> tuple[str, ...]:
    phase2 = state.analysis_outputs.get("phase2", {})
    if not isinstance(phase2, Mapping):
        raise StrategyValidationError(["Decision V2 phase2 output must be structured"])
    raw = phase2.get("uncertainties", [])
    if not isinstance(raw, (list, tuple)):
        raise StrategyValidationError(["Decision V2 uncertainties must be an ordered collection"])
    return tuple(_text(item, f"Decision V2 uncertainty {index}") for index, item in enumerate(raw, start=1))


def build_strategy_input(
    state: DecisionState,
    execution: AnalysisExecution,
    *,
    source_decision_id: int | None = None,
    source_reference: str | None = None,
) -> StrategyInput:
    """Translate completed, validated Decision V2 artifacts without reasoning.

    ``DecisionRequest.objective`` is authoritative. Phase 2 goals are contextual
    enrichments and are intentionally not merged into or substituted for it.
    """

    if not isinstance(state, DecisionState):
        raise StrategyValidationError(["state must be a DecisionState"])
    if not isinstance(execution, AnalysisExecution):
        raise StrategyValidationError(["execution must be an AnalysisExecution"])
    if execution.status != "READY" or execution.result is None:
        raise StrategyValidationError(["a completed READY Decision V2 execution is required"])

    analysis = execution.result
    evidence_by_id = {item.id: item for item in state.evidence}
    evidence_refs = tuple(
        EvidenceReference(
            evidence_id=_text(evidence_id, f"Decision V2 evidence reference {index}"),
            citation_label=evidence_by_id.get(evidence_id).citation_label
            if evidence_id in evidence_by_id else None,
        )
        for index, evidence_id in enumerate(analysis.evidence_used, start=1)
    )
    assumptions = tuple(
        StrategyAssumption(_text(item.statement, "Decision V2 assumption"), _text(item.source, "Decision V2 assumption source"))
        for item in state.assumptions
    ) + tuple(
        StrategyAssumption(_text(item, "Decision V2 analysis assumption"), "decision_analysis")
        for item in analysis.assumptions_used
    )

    try:
        confidence = ConfidenceLevel(execution.confidence)
    except (TypeError, ValueError) as error:
        raise StrategyValidationError(["completed Decision V2 confidence must be HIGH, MODERATE, or LOW"]) from error

    strategy_input = StrategyInput(
        scope=StrategyScope(
            user_id=state.request.user_id,
            organization_id=state.request.organization_id,
            workspace_id=state.request.workspace_id,
        ),
        source_decision_id=source_decision_id,
        source_reference=source_reference,
        decision_type=state.request.decision_type,
        objective=_text(state.request.objective, "Decision V2 objective"),
        chosen_direction=_text(analysis.recommendation.recommended_option, "Decision V2 recommendation"),
        considered_alternatives=tuple(
            StrategyAlternative(
                name=_text(item.option, f"Decision V2 alternative {index}"),
                # Decision V2 exposes an option, not a separate strategic approach.
                # Preserve that exact direction instead of inventing expansion text.
                approach=_text(item.option, f"Decision V2 alternative {index}"),
            )
            for index, item in enumerate(analysis.alternatives, start=1)
        ),
        constraints=tuple(
            StrategyConstraint(f"decision-constraint-{index:03d}", _text(item, f"Decision V2 constraint {index}"))
            for index, item in enumerate(state.request.constraints, start=1)
        ),
        resources=_resources(state),
        evidence_refs=evidence_refs,
        assumptions=assumptions,
        risks=tuple(StrategyRisk(_text(item, f"Decision V2 risk {index}")) for index, item in enumerate(analysis.risks, start=1)),
        uncertainties=_uncertainties(state),
        time_horizon=state.request.timeframe.strip() if isinstance(state.request.timeframe, str) and state.request.timeframe.strip() else None,
        change_conditions=tuple(
            _text(item, f"Decision V2 change condition {index}")
            for index, item in enumerate(analysis.recommendation.what_would_change_the_recommendation, start=1)
        ),
        confidence=confidence,
        confidence_rationale=tuple(
            _text(item, f"Decision V2 confidence rationale {index}")
            for index, item in enumerate(execution.confidence_rationale, start=1)
        ),
    )
    validate_strategy_input(strategy_input)
    return strategy_input
