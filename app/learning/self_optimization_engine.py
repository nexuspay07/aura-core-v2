# Self-Optimization Engine
import random
from typing import Dict
from app.learning.self_optimization_engine import self_optimization_engine


class SelfOptimizationEngine:

    def __init__(self):
        print("[SELF-OPTIMIZATION ENGINE] Adaptive optimization enabled")

    def optimize(self, strategies: Dict[int, Dict], learning_bias: Dict[str, float]) -> Dict[str, float]:
        """
        Adjust internal strategy parameters based on performance
        strategies: {id: {"fitness": float, "type": str}}
        learning_bias: current action biases
        """
        print("[SELF-OPTIMIZATION] Evaluating strategies...")

        # Example: tweak biases based on strategy fitness
        for sid, data in strategies.items():
            fitness = data.get("fitness", 0.5)
            if fitness < 0.5:
                learning_bias[data["type"]] += 0.05  # encourage underused actions
            elif fitness > 0.8:
                learning_bias[data["type"]] -= 0.02  # slightly reduce overused actions

        # Clamp biases between 0.1 and 0.5
        for key in learning_bias:
            learning_bias[key] = max(0.1, min(learning_bias[key], 0.5))

        print(f"[SELF-OPTIMIZATION] Updated learning bias: {learning_bias}")
        return learning_bias

# Global instance
self_optimization_engine = SelfOptimizationEngine()