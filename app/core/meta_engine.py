import time
from typing import Dict, Any


class MetaEngine:

    def __init__(self):

        self.reflections = []

        print("[META ENGINE] Meta-Cognitive Reflection Enabled")

    # ==========================================
    # Reflect on Experience
    # ==========================================

    def reflect(
        self,
        goal: Dict[str, Any],
        plan: Dict[str, Any],
        score: float
    ):

        try:

            reflection = {
                "goal": goal.get("name", "unknown"),
                "actions": plan.get("actions", []),
                "score": score,
                "timestamp": time.time()
            }

            self.reflections.append(reflection)

            print(
                f"[META ENGINE] Reflection stored | "
                f"Goal: {reflection['goal']} | "
                f"Score: {reflection['score']}"
            )

        except Exception as e:

            print(f"[META ENGINE ERROR] {e}")


# Global instance
meta_engine = MetaEngine()