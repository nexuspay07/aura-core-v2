from datetime import datetime
from typing import List, Dict, Any


class AdaptiveCore:

    def __init__(self):
        self.learning_rate = 0.01
        self.total_adaptations = 0
        self.experiences: List[Dict[str, Any]] = []

    # REQUIRED METHOD — this is what router calls
    def learn(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:

        if memories is None:
            memories = []

        # Store experiences
        for memory in memories:
            self.experiences.append({
                "memory": memory,
                "timestamp": datetime.utcnow().isoformat()
            })

        # Adapt learning rate
        adaptation_boost = len(memories) * 0.001
        self.learning_rate += adaptation_boost

        # Track adaptations
        self.total_adaptations += len(memories)

        return {
            "learning_rate": round(self.learning_rate, 6),
            "total_adaptations": self.total_adaptations,
            "experiences": len(self.experiences),
            "timestamp": datetime.utcnow().isoformat(),
            "adaptive": True
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "learning_rate": round(self.learning_rate, 6),
            "total_adaptations": self.total_adaptations,
            "experiences": len(self.experiences),
            "adaptive_active": True
        }


# Global instance (REQUIRED)
adaptive_core = AdaptiveCore()