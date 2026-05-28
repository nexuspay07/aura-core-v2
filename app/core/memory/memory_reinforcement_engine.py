# app/core/memory/memory_reinforcement_engine.py

from datetime import datetime


class MemoryReinforcementEngine:

    def __init__(self):
        print("[MEMORY REINFORCEMENT ENGINE] Initialized")

    def reinforce_memory(
        self,
        memory_text: str,
        outcome_score: float,
        usage_count: int,
        strategic_value: float
    ):

        reinforcement_strength = (
            (outcome_score * 5)
            + (usage_count * 1.5)
            + (strategic_value * 10)
        )

        if reinforcement_strength >= 40:
            reinforcement_level = "permanent"

        elif reinforcement_strength >= 25:
            reinforcement_level = "strong"

        elif reinforcement_strength >= 10:
            reinforcement_level = "moderate"

        else:
            reinforcement_level = "weak"

        return {
            "memory": memory_text,
            "reinforcement_strength": round(reinforcement_strength, 2),
            "reinforcement_level": reinforcement_level,
            "reinforced_at": datetime.utcnow().isoformat()
        }


memory_reinforcement_engine = MemoryReinforcementEngine()