"""Canonical, side-effect-free Strategy domain contracts."""

from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAlternative,
    StrategyAssumption,
    StrategyConstraint,
    StrategyInput,
    StrategyPhase,
    StrategyResource,
    StrategyResult,
    StrategyRisk,
    StrategyScope,
    SuccessMeasure,
)
from app.strategy.validation import (
    StrategyValidationError,
    validate_constraint_preservation,
    validate_strategy_input,
    validate_strategy_result,
)

__all__ = [
    "ConfidenceLevel",
    "EvidenceReference",
    "StrategyAlternative",
    "StrategyAssumption",
    "StrategyConstraint",
    "StrategyInput",
    "StrategyPhase",
    "StrategyResource",
    "StrategyResult",
    "StrategyRisk",
    "StrategyScope",
    "StrategyValidationError",
    "SuccessMeasure",
    "validate_constraint_preservation",
    "validate_strategy_input",
    "validate_strategy_result",
]
