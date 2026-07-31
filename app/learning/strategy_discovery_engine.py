import logging
import random
import uuid
from typing import Any, Dict, List, Optional

from app.learning.strategy_registry import Strategy, strategy_registry
from app.services.kpi_service import kpi_service

logger = logging.getLogger(__name__)


class StrategyDiscoveryEngine:
    """
    Strategy Discovery Engine.

    Responsible for learning new strategies from
    successful execution plans.
    """

    def __init__(self):

        self.discovery_rate = 0.30

        logger.info("Strategy Discovery Engine initialized.")

    # ==========================================================
    # DISCOVER STRATEGY
    # ==========================================================

    def discover_strategy(
        self,
        goal: str,
        plan: List[Any],
        score: float,
    ) -> Optional[Strategy]:
        """
        Analyze a successful execution and create a
        reusable strategy if appropriate.
        """

        if score < 0.7:
            return None

        if random.random() > self.discovery_rate:
            return None

        strategy = Strategy(
            strategy_id=f"strategy_{uuid.uuid4().hex[:8]}",
            name=f"Discovered Strategy",
            parameters=self.extract_parameters_from_plan(plan),
        )

        strategy_registry.register_strategy(strategy)

        kpi_service.record_strategy_discovered()

        logger.info(
            "Discovered new strategy: %s",
            strategy.strategy_id,
        )

        return strategy

    # ==========================================================
    # PARAMETER EXTRACTION
    # ==========================================================

    def extract_parameters_from_plan(
        self,
        plan: List[Any],
    ) -> Dict[str, Any]:

        step_count = len(plan)

        return {
            "complexity": step_count,
            "planning_depth": min(step_count, 10),
            "risk": round(random.uniform(0.2, 0.8), 2),
        }

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    def set_discovery_rate(
        self,
        rate: float,
    ) -> None:

        self.discovery_rate = max(0.0, min(rate, 1.0))

    def get_discovery_rate(self) -> float:

        return self.discovery_rate


# ==========================================================
# GLOBAL INSTANCE
# ==========================================================

strategy_discovery_engine = StrategyDiscoveryEngine()