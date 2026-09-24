"""Internal application boundary for invoking Strategy Intelligence."""

from __future__ import annotations

from collections.abc import Callable

from app.intelligence_v2.contracts import AnalysisExecution, DecisionState
from app.strategy.adapters import build_strategy_input
from app.strategy.contracts import StrategyInput, StrategyResult
from app.strategy.orchestrator import StrategyOrchestrator, strategy_orchestrator


class StrategyCapability:
    """Invoke canonical Strategy for inputs authorized by the caller.

    This boundary performs no authentication, authorization, tenant lookup, or
    persistence. ``StrategyInput.scope`` is treated as already authorized.
    """

    def __init__(self, orchestrator: StrategyOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or strategy_orchestrator

    def generate(
        self,
        strategy_input: StrategyInput,
        *,
        before_provider_attempt: Callable[[], None] | None = None,
    ) -> StrategyResult:
        """Generate a strategy through the canonical orchestrator."""

        if before_provider_attempt is None:
            return self._orchestrator.generate(strategy_input)
        return self._orchestrator.generate(strategy_input, before_provider_attempt=before_provider_attempt)

    def generate_from_decision(
        self,
        state: DecisionState,
        execution: AnalysisExecution,
        *,
        source_decision_id: int | None = None,
        source_reference: str | None = None,
    ) -> StrategyResult:
        """Generate from completed authoritative Decision V2 artifacts."""

        strategy_input = build_strategy_input(
            state,
            execution,
            source_decision_id=source_decision_id,
            source_reference=source_reference,
        )
        return self.generate(strategy_input)


strategy_capability = StrategyCapability()
