"""Canonical, side-effect-free Strategy domain contracts."""

from app.strategy.adapters import build_strategy_input
from app.strategy.orchestrator import StrategyGenerationError, StrategyOrchestrator, strategy_orchestrator
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
    "build_strategy_input",
    "EvidenceReference",
    "StrategyAlternative",
    "StrategyAssumption",
    "StrategyConstraint",
    "StrategyInput",
    "StrategyGenerationError",
    "StrategyOrchestrator",
    "StrategyPhase",
    "StrategyResource",
    "StrategyResult",
    "StrategyRisk",
    "StrategyScope",
    "StrategyValidationError",
    "strategy_orchestrator",
    "SuccessMeasure",
    "validate_constraint_preservation",
    "validate_strategy_input",
    "validate_strategy_result",
]
