import uuid
from datetime import datetime


class EvolutionEngine:
    def __init__(self, memory_manager, decision_engine):
        self.memory_manager = memory_manager
        self.decision_engine = decision_engine

        self.evolution_history = []
        self.intelligence_version = 1.0
        self.evolution_score = 0

    def analyze_self(self, organization_id: str):
        """
        Analyze past decisions and detect improvement opportunities
        """

        decisions = self.decision_engine.get_decision_history()

        total = len(decisions)

        if total == 0:
            return {
                "status": "no_data",
                "message": "No decisions available for evolution"
            }

        confidence_sum = sum(d.get("confidence", 0) for d in decisions)
        avg_confidence = confidence_sum / total

        evolution_needed = avg_confidence < 0.75

        return {
            "total_decisions": total,
            "average_confidence": avg_confidence,
            "evolution_needed": evolution_needed
        }

    def evolve(self, organization_id: str):
        """
        Improve intelligence based on analysis
        """

        analysis = self.analyze_self(organization_id)

        if analysis.get("status") == "no_data":
            return analysis

        if analysis["evolution_needed"]:
            self.intelligence_version += 0.1
            self.evolution_score += 1

            evolution_record = {
                "id": str(uuid.uuid4()),
                "organization_id": organization_id,
                "version": round(self.intelligence_version, 2),
                "score": self.evolution_score,
                "timestamp": datetime.utcnow().isoformat(),
                "improvement": "Decision confidence optimization"
            }

            self.evolution_history.append(evolution_record)

            # Store evolution in memory
            self.memory_manager.store_memory(
                organization_id=organization_id,
                memory_type="evolution",
                content=f"System evolved to version {self.intelligence_version}"
            )

            return {
                "status": "evolved",
                "new_version": self.intelligence_version,
                "evolution_score": self.evolution_score
            }

        return {
            "status": "stable",
            "version": self.intelligence_version,
            "message": "No evolution needed"
        }

    def get_status(self):
        return {
            "intelligence_version": self.intelligence_version,
            "evolution_score": self.evolution_score,
            "total_evolutions": len(self.evolution_history)
        }

    def get_history(self):
        return self.evolution_history