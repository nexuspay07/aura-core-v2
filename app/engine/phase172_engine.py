# app/engine/phase172_engine.py

from app.simulators.hospital_simulator import hospital
from app.simulators.kpi_tracker import kpi_tracker
from app.learning.reinforcement_memory import reinforcement_memory
from app.learning.strategy_evolution_engine import strategy_evolution_engine
from app.learning.strategy_fitness_engine import strategy_fitness_engine
from app.learning.strategy_registry import strategy_registry

class Phase172Engine:
    """
    Phase 172 Engine: Context-Aware Strategy Evolution
    Enhances decision making with meta-memory, context tracking, and KPI-driven fitness.
    """

    def __init__(self):
        print("[PHASE 172 ENGINE] Initialized")

    def execute(self, action=None):
        # -----------------------------
        # 1. Observe current hospital state
        # -----------------------------
        state_before = hospital.get_state()
        kpis_before = state_before.copy()

        # -----------------------------
        # 2. Decide action if not passed
        # -----------------------------
        if action is None:
            action = "do_nothing"
            wait_time = state_before.get("wait_time", 0)
            capacity = state_before.get("capacity", 0)
            
            if wait_time > 40:
                action = "allocate_staff"
            elif capacity < 50:
                action = "open_beds"
        
        # -----------------------------
        # 3. Apply action to simulator
        # -----------------------------
        result = hospital.apply_action(action)
        kpis_after = hospital.get_state()
        kpi_tracker.record(kpis_after)

        # -----------------------------
        # 4. Calculate fitness
        # -----------------------------
        fitness_data = strategy_fitness_engine.calculate_fitness(kpis_after)

        # Determine context dynamically
        context = self._determine_context(kpis_after)
        
        # -----------------------------
        # 5. Evolve strategy using Phase 172 logic
        # -----------------------------
        evolution = strategy_evolution_engine.evolve(
            action=action,
            fitness_score=fitness_data["fitness"],
            kpis=kpis_after,
            context=context
        )

        # -----------------------------
        # 6. Calculate reward
        # -----------------------------
        reward = 0
        if kpis_after["wait_time"] < kpis_before["wait_time"]:
            reward += 2
        if kpis_after["patients"] < kpis_before["patients"]:
            reward += 1
        if kpis_after["capacity"] > kpis_before["capacity"]:
            reward += 1

        # -----------------------------
        # 7. Store reinforcement experience
        # -----------------------------
        reinforcement_memory.store_experience(
            action=action,
            reward=reward,
            state=kpis_after
        )

        # -----------------------------
        # 8. Update strategy registry
        # -----------------------------
        strategy_registry.record_use(action, reward)

        # -----------------------------
        # 9. Return full result
        # -----------------------------
        return {
            "action": action,
            "result": result,
            "kpis": kpis_after,
            "reward": reward,
            "evolution": evolution,
            "fitness": fitness_data,
            "context": context
        }

    def _determine_context(self, kpis):
        """
        Generates a simple context string based on KPIs.
        Can be extended with more sophisticated logic.
        """
        wait = kpis.get("wait_time", 0)
        capacity = kpis.get("capacity", 0)
        if wait > 50 and capacity < 50:
            return "high_wait_low_capacity"
        elif wait > 40:
            return "high_wait"
        elif capacity < 50:
            return "low_capacity"
        else:
            return "normal"

# Singleton for Phase 172 engine
phase172_engine = Phase172Engine()