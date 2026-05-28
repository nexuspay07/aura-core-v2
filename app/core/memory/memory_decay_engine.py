# app/core/memory/memory_decay_engine.py

from datetime import datetime


class MemoryDecayEngine:

    def __init__(self):
        print("[MEMORY DECAY ENGINE] Initialized")

    def calculate_decay(
        self,
        importance_score: float,
        hours_since_access: float,
        reinforcement_count: int = 0
    ):

        decay_rate = hours_since_access * 0.05

        reinforcement_bonus = reinforcement_count * 2

        remaining_strength = (
            importance_score
            - decay_rate
            + reinforcement_bonus
        )

        remaining_strength = max(0, remaining_strength)

        if remaining_strength >= 40:
            status = "persistent"

        elif remaining_strength >= 20:
            status = "stable"

        elif remaining_strength >= 5:
            status = "weakening"

        else:
            status = "forgettable"

        return {
            "original_importance": importance_score,
            "hours_since_access": hours_since_access,
            "reinforcement_count": reinforcement_count,
            "remaining_strength": round(remaining_strength, 2),
            "memory_status": status,
            "evaluated_at": datetime.utcnow().isoformat()
        }


memory_decay_engine = MemoryDecayEngine()