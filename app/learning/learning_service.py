import logging
from typing import Any, Dict, List, Optional

from app.learning.strategy_discovery_engine import strategy_discovery_engine
from app.learning.strategy_darwin_engine import strategy_darwin_engine
from app.learning.strategy_evolution_engine import strategy_evolution_engine
from app.learning.strategy_simulation_engine import run_simulation

logger = logging.getLogger(__name__)


class LearningService:
    """
    Central coordinator for Aura's learning subsystem.

    Responsibilities:
    - Discover new strategies
    - Select the best strategy
    - Record performance
    - Evolve strategies
    - Run simulations
    """

    # ==========================================================
    # DISCOVERY
    # ==========================================================

    def discover(
        self,
        goal: str,
        plan: List[Any],
        score: float,
    ):
        return strategy_discovery_engine.discover_strategy(
            goal=goal,
            plan=plan,
            score=score,
        )

    # ==========================================================
    # DARWIN SELECTION
    # ==========================================================

    def select_strategy(self) -> Optional[str]:
        return strategy_darwin_engine.select_best_strategy()

    # ==========================================================
    # RECORD RESULT
    # ==========================================================

    def record_result(
        self,
        strategy_id: str,
        fitness: float,
    ) -> None:
        strategy_darwin_engine.record_strategy_result(
            strategy_id,
            fitness,
        )

    # ==========================================================
    # EVOLUTION
    # ==========================================================

    def evolve(self) -> None:
        strategy_evolution_engine.evolve_strategies()

    # ==========================================================
    # SIMULATION
    # ==========================================================

    def simulate(self):
        return run_simulation()

    # ==========================================================
    # COMPLETE LEARNING CYCLE
    # ==========================================================

    def run_learning_cycle(
        self,
        goal: str,
        plan: List[Any],
        score: float,
    ) -> Dict:

        discovered = self.discover(
            goal,
            plan,
            score,
        )

        self.evolve()

        selected = self.select_strategy()

        simulation = self.simulate()

        logger.info("Learning cycle completed.")

        return {
            "discovered_strategy": discovered,
            "selected_strategy": selected,
            "simulation_results": simulation,
        }


learning_service = LearningService()