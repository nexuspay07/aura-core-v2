"""Deterministic reconciliation from live or snapshotted Decision intelligence."""
from __future__ import annotations
from app.intelligence_v2.contracts import AnalysisExecution, DecisionState, DecisionType
from app.intelligence_v2.decision_snapshot import CanonicalDecisionSnapshotV1, DecisionSnapshotValidationError
from app.strategy.contracts import ConfidenceLevel, EvidenceReference, StrategyAlternative, StrategyAssumption, StrategyConstraint, StrategyInput, StrategyResource, StrategyRisk, StrategyScope
from app.strategy.validation import StrategyValidationError, validate_strategy_input

def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise StrategyValidationError([f"{field} must be meaningful"])
    return value.strip()

def build_strategy_input(state: DecisionState, execution: AnalysisExecution, *, source_decision_id: int | None = None, source_reference: str | None = None) -> StrategyInput:
    if not isinstance(state, DecisionState): raise StrategyValidationError(["state must be a DecisionState"])
    if not isinstance(execution, AnalysisExecution): raise StrategyValidationError(["execution must be an AnalysisExecution"])
    if execution.status != "READY" or execution.result is None: raise StrategyValidationError(["a completed READY Decision V2 execution is required"])
    try:
        snapshot = CanonicalDecisionSnapshotV1.capture(state, execution)
    except DecisionSnapshotValidationError as error:
        raise StrategyValidationError([str(error).replace("selected option", "recommendation").replace("alternative option", "recommendation")]) from error
    return build_strategy_input_from_snapshot(snapshot, scope=StrategyScope(user_id=state.request.user_id, organization_id=state.request.organization_id, workspace_id=state.request.workspace_id), source_decision_id=source_decision_id, source_reference=source_reference)

def build_strategy_input_from_snapshot(snapshot: CanonicalDecisionSnapshotV1, *, scope: StrategyScope, source_decision_id: int | None = None, source_reference: str | None = None) -> StrategyInput:
    if not isinstance(snapshot, CanonicalDecisionSnapshotV1): raise StrategyValidationError(["snapshot must be a CanonicalDecisionSnapshotV1"])
    try: confidence = ConfidenceLevel(snapshot.confidence)
    except (TypeError, ValueError) as error: raise StrategyValidationError(["snapshot confidence must be HIGH, MODERATE, or LOW"]) from error
    result = StrategyInput(
        scope=scope, source_decision_id=source_decision_id, source_reference=source_reference,
        decision_type=DecisionType(snapshot.decision_type), objective=snapshot.objective, chosen_direction=snapshot.selected_option,
        considered_alternatives=tuple(StrategyAlternative(name=_text(item["option"], f"Decision V2 alternative {i}"), approach=_text(item["option"], f"Decision V2 alternative {i}")) for i, item in enumerate(snapshot.alternatives, 1)),
        constraints=tuple(StrategyConstraint(f"decision-constraint-{i:03d}", _text(item, f"Decision V2 constraint {i}")) for i, item in enumerate(snapshot.constraints, 1)),
        resources=tuple(StrategyResource(name=item["type"], description=item["value"]) for item in snapshot.resources),
        evidence_refs=tuple(EvidenceReference(evidence_id=item["evidence_id"], citation_label=item["citation_label"]) for item in snapshot.evidence_references),
        assumptions=tuple(StrategyAssumption(item["statement"], item["source"]) for item in snapshot.assumptions),
        risks=tuple(StrategyRisk(item) for item in snapshot.risks), uncertainties=snapshot.uncertainties,
        time_horizon=snapshot.time_horizon, change_conditions=snapshot.change_conditions,
        confidence=confidence, confidence_rationale=snapshot.confidence_rationale,
    )
    validate_strategy_input(result)
    return result
