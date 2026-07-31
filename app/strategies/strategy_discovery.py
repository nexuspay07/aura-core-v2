import logging
import random
import uuid
from typing import Dict, List, Optional

from app.services.kpi_service import kpi_service
from app.strategies.strategy_registry import strategy_registry

logger = logging.getLogger(__name__)


class StrategyDiscoveryEngine:
    """
    Phase 174
    Autonomous Strategy Discovery Engine.

    Responsible for generating new candidate strategies,
    registering them, and tracking their fitness.
    """

    def __init__(self):
        self.discovered_strategies: Dict[str, Dict] = {}

        self.strategy_templates = [
            "explore_then_optimize",
            "reflect_then_plan",
            "fast_execution",
            "deep_analysis",
            "risk_balanced",
            "resource_efficient",
            "parallel_decision",
            "memory_guided",
        ]

        logger.info("Strategy Discovery Engine initialized.")

    # ---------------------------------------------------
    # DISCOVER STRATEGY
    # ---------------------------------------------------

    def discover_strategy(self) -> Dict:
        """
        Generate a new strategy candidate.
        """

        template = random.choice(self.strategy_templates)

        strategy = {
            "id": f"strategy_{uuid.uuid4().hex[:6]}",
            "template": template,
            "fitness": 0,
            "uses": 0,
        }

        self.discovered_strategies[strategy["id"]] = strategy

        # Register globally (if supported)
        if hasattr(strategy_registry, "register_strategy"):
            strategy_registry.register_strategy(strategy)

        # Record KPI
        try:
            kpi_service.record_strategy_discovered()
        except Exception:
            logger.exception("Failed to record strategy discovery KPI.")

        logger.info(
            "Discovered strategy %s (%s)",
            strategy["id"],
            template,
        )

        return strategy

    # ---------------------------------------------------
    # GET STRATEGY
    # ---------------------------------------------------

    def get_strategy(
        self,
        strategy_id: str,
    ) -> Optional[Dict]:

        return self.discovered_strategies.get(strategy_id)

    # ---------------------------------------------------
    # LIST STRATEGIES
    # ---------------------------------------------------

    def list_strategies(self) -> List[Dict]:

        return list(self.discovered_strategies.values())

    # ---------------------------------------------------
    # UPDATE FITNESS
    # ---------------------------------------------------

    def update_fitness(
        self,
        strategy_id: str,
        reward: float,
    ) -> Optional[Dict]:

        strategy = self.discovered_strategies.get(strategy_id)

        if strategy is None:
            return None

        strategy["fitness"] += reward
        strategy["uses"] += 1

        logger.info(
            "Updated strategy %s | reward=%s | fitness=%s | uses=%s",
            strategy_id,
            reward,
            strategy["fitness"],
            strategy["uses"],
        )

        return strategy

    # ---------------------------------------------------
    # TOTAL DISCOVERED
    # ---------------------------------------------------

    def total_strategies(self) -> int:

        return len(self.discovered_strategies)

    # ---------------------------------------------------
    # CLEAR
    # ---------------------------------------------------

    def clear(self):

        self.discovered_strategies.clear()

        logger.info("Strategy Discovery Engine cleared.")


# ==========================================================
# GLOBAL INSTANCE
# ==========================================================

strategy_discovery_engine = StrategyDiscoveryEngine()