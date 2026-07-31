import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==========================================================
# STRATEGY MODEL
# ==========================================================

@dataclass
class Strategy:
    strategy_id: str
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


# ==========================================================
# STRATEGY REGISTRY
# ==========================================================

class StrategyRegistry:
    """
    Central registry for every strategy known by Aura.
    """

    def __init__(self):
        self._strategies: Dict[str, Strategy] = {}
        self._lock = Lock()

        self.register_strategy(
            Strategy(
                strategy_id="exploration",
                name="Exploration Strategy",
                parameters={"risk": 0.8},
            )
        )

        self.register_strategy(
            Strategy(
                strategy_id="efficiency",
                name="Efficiency Strategy",
                parameters={"speed": 0.9},
            )
        )

        self.register_strategy(
            Strategy(
                strategy_id="balanced",
                name="Balanced Strategy",
                parameters={"balance": 0.5},
            )
        )

        logger.info("Strategy Registry initialized.")

    # ---------------------------------------------------------

    def register_strategy(self, strategy: Strategy) -> None:
        with self._lock:
            self._strategies[strategy.strategy_id] = strategy

        logger.info("Registered strategy: %s", strategy.strategy_id)

    # ---------------------------------------------------------

    def get_strategy(
        self,
        strategy_id: str,
    ) -> Optional[Strategy]:

        return self._strategies.get(strategy_id)

    # ---------------------------------------------------------

    def get_all_strategies(self) -> List[Strategy]:

        return list(self._strategies.values())

    # ---------------------------------------------------------

    def strategy_exists(
        self,
        strategy_id: str,
    ) -> bool:

        return strategy_id in self._strategies

    # ---------------------------------------------------------

    def remove_strategy(
        self,
        strategy_id: str,
    ) -> bool:

        with self._lock:

            if strategy_id not in self._strategies:
                return False

            del self._strategies[strategy_id]

        logger.info("Removed strategy: %s", strategy_id)

        return True

    # ---------------------------------------------------------

    def total_strategies(self) -> int:

        return len(self._strategies)

    # ---------------------------------------------------------

    def clear(self) -> None:

        with self._lock:
            self._strategies.clear()

        logger.info("Strategy Registry cleared.")


# ==========================================================
# GLOBAL INSTANCE
# ==========================================================

strategy_registry = StrategyRegistry()


# ==========================================================
# CONVENIENCE FUNCTIONS
# ==========================================================

def get_all_strategies() -> List[Strategy]:
    return strategy_registry.get_all_strategies()