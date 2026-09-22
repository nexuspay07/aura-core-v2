"""Pure structural validation for canonical Strategy contracts."""

from __future__ import annotations

from dataclasses import fields

from app.strategy.contracts import ConfidenceLevel, StrategyInput, StrategyResult, StrategyScope


class StrategyValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


_FORBIDDEN_FIELDS = {
    "actual_outcome", "execution_command", "execution_progress", "execution_status",
    "marketplace_publication", "reward", "rl_state", "simulation_result",
    "simulated_world_state", "task_assignee", "tool_execution",
}


def _meaningful(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _scope_errors(scope: StrategyScope) -> list[str]:
    errors = []
    if not isinstance(scope, StrategyScope):
        return ["scope must be a StrategyScope"]
    if not isinstance(scope.user_id, int) or isinstance(scope.user_id, bool) or scope.user_id <= 0:
        errors.append("scope.user_id must be a positive integer")
    for name in ("organization_id", "workspace_id"):
        value = getattr(scope, name)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            errors.append(f"scope.{name} must be a positive integer when supplied")
    return errors


def _common_errors(value: StrategyInput | StrategyResult) -> list[str]:
    errors = _scope_errors(value.scope)
    if not _meaningful(value.objective): errors.append("objective must be meaningful")
    if not _meaningful(value.chosen_direction): errors.append("chosen_direction must be meaningful")
    if not isinstance(value.confidence, ConfidenceLevel): errors.append("confidence must use an Aevric ConfidenceLevel")
    if not value.confidence_rationale or any(not _meaningful(item) for item in value.confidence_rationale):
        errors.append("confidence_rationale must contain meaningful text")
    if value.source_decision_id is not None and (not isinstance(value.source_decision_id, int) or isinstance(value.source_decision_id, bool) or value.source_decision_id <= 0):
        errors.append("source_decision_id must be a positive integer when supplied")
    if value.source_reference is not None and not _meaningful(value.source_reference):
        errors.append("source_reference must be meaningful when supplied")
    if any(not _meaningful(item.constraint_id) or not _meaningful(item.statement) for item in value.constraints):
        errors.append("constraints require stable identifiers and meaningful statements")
    constraint_ids = [item.constraint_id.strip().casefold() for item in value.constraints]
    if len(constraint_ids) != len(set(constraint_ids)): errors.append("constraint identifiers must be unique")
    if any(not _meaningful(item.evidence_id) for item in value.evidence_refs):
        errors.append("evidence references require an evidence_id")
    evidence_ids = [item.evidence_id.strip() for item in value.evidence_refs]
    if len(evidence_ids) != len(set(evidence_ids)): errors.append("evidence references must be unique")
    if any(not _meaningful(item.statement) or not _meaningful(item.source) for item in value.assumptions):
        errors.append("assumptions require an explicit statement and source")
    if any(not _meaningful(item.risk) or (item.mitigation is not None and not _meaningful(item.mitigation)) for item in value.risks):
        errors.append("risks require meaningful text and a meaningful mitigation when supplied")
    if any(not _meaningful(item) for item in value.change_conditions):
        errors.append("change_conditions must contain meaningful text")
    contract_fields = {item.name for item in fields(value)}
    forbidden = sorted(contract_fields & _FORBIDDEN_FIELDS)
    if forbidden: errors.append(f"cross-boundary fields are forbidden: {', '.join(forbidden)}")
    return errors


def _raise(errors: list[str]) -> None:
    if errors: raise StrategyValidationError(errors)


def validate_strategy_input(value: StrategyInput) -> None:
    if not isinstance(value, StrategyInput): raise StrategyValidationError(["value must be a StrategyInput"])
    errors = _common_errors(value)
    _raise(errors)


def validate_constraint_preservation(source: StrategyInput, result: StrategyResult) -> None:
    source_constraints = {item.constraint_id.strip().casefold(): item.statement.strip() for item in source.constraints}
    result_constraints = {item.constraint_id.strip().casefold(): item.statement.strip() for item in result.constraints}
    missing = sorted(key for key, statement in source_constraints.items() if result_constraints.get(key) != statement)
    if missing: raise StrategyValidationError([f"result does not preserve constraints: {', '.join(missing)}"])
    if source.source_decision_id is not None and result.source_decision_id != source.source_decision_id:
        raise StrategyValidationError(["result does not preserve source_decision_id"])
    if source.source_reference is not None and result.source_reference != source.source_reference:
        raise StrategyValidationError(["result does not preserve source_reference"])
    if result.scope != source.scope:
        raise StrategyValidationError(["result does not preserve tenant scope"])
    source_evidence = {item.evidence_id for item in source.evidence_refs}
    result_evidence = {item.evidence_id for item in result.evidence_refs}
    missing_evidence = sorted(source_evidence - result_evidence)
    if missing_evidence:
        raise StrategyValidationError([f"result does not preserve evidence references: {', '.join(missing_evidence)}"])


def validate_strategy_result(value: StrategyResult, source: StrategyInput | None = None) -> None:
    if not isinstance(value, StrategyResult): raise StrategyValidationError(["value must be a StrategyResult"])
    errors = _common_errors(value)
    if not _meaningful(value.approach): errors.append("approach must be meaningful")
    if not value.phases: errors.append("at least one strategic phase is required")
    orders = []
    for phase in value.phases:
        if not isinstance(phase.order, int) or isinstance(phase.order, bool) or phase.order <= 0:
            errors.append("phase order must be a positive integer")
        else: orders.append(phase.order)
        if not _meaningful(phase.name) or not _meaningful(phase.purpose):
            errors.append("phases require a meaningful name and purpose")
        if any(not _meaningful(item) for item in phase.focus_areas):
            errors.append("phase focus areas must contain meaningful text")
        if phase.milestone_intent is not None and not _meaningful(phase.milestone_intent):
            errors.append("phase milestone_intent must be meaningful when supplied")
    if len(orders) != len(set(orders)): errors.append("phase order must be unique")
    if orders and orders != list(range(1, len(orders) + 1)):
        errors.append("phases must be supplied in contiguous order starting at 1")
    if not value.success_measures:
        errors.append("at least one success measure is required")
    elif any(not _meaningful(item.condition) for item in value.success_measures):
        errors.append("success measures must contain meaningful conditions")
    if not value.change_conditions:
        errors.append("at least one change condition is required")
    if value.version is not None and (not isinstance(value.version, int) or isinstance(value.version, bool) or value.version <= 0):
        errors.append("version must be a positive integer when supplied")
    _raise(errors)
    if source is not None:
        validate_strategy_input(source)
        validate_constraint_preservation(source, value)
