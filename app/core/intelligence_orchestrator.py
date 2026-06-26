from datetime import datetime
from app.core.response_composer_engine import response_composer_engine


class IntelligenceOrchestrator:
    """
    Light orchestration layer for Aura.
    Tracks events and prepares for future multi-engine coordination.
    """

    def __init__(self):
        self.total_requests = 0
        self.last_event = None

    def process_event(self, event: dict):
        self.total_requests += 1

        enriched_event = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "id": self.total_requests,
            "type": event.get("type", "unknown")
        }

        self.last_event = enriched_event

        print(f"[INTELLIGENCE] Event #{self.total_requests} ({enriched_event['type']})")

        return enriched_event

    def route_intent(self, intent: str):
        """
        Decide which system should handle the request.
        (basic version)
        """

        if intent == "healthcare_strategy":
            return "healthcare"

        if intent == "business_strategy":
            return "simulation"

        if intent == "finance_strategy":
            return "simulation"

        return "general"

    def enrich_context(self, context: dict):
        """
        Add metadata for downstream engines
        """
        context["orchestrated"] = True
        context["request_count"] = self.total_requests
        return context

    def status(self):
        return {
            "total_requests": self.total_requests,
            "last_event": self.last_event
        }

    # ==========================================================
    # 🔥 PHASE 66.5 — RESPONSE COMPOSER INTEGRATION LAYER
    # ==========================================================

    def compose_final_response(
        self,
        goal,
        executive_synthesis,
        market_intelligence,
        competitive_intelligence,
        dynamic_reasoning,
        operational_intelligence,
        simulation
    ):
        """
        This is the FINAL EXECUTION LAYER of Aura AI.

        It converts raw intelligence outputs into human-readable executive response.
        """

        return response_composer_engine.compose(
            goal=goal,
            executive_synthesis=executive_synthesis,
            market_intelligence=market_intelligence,
            competitive_intelligence=competitive_intelligence,
            dynamic_reasoning=dynamic_reasoning,
            operational_intelligence=operational_intelligence,
            simulation=simulation
        )


# ==========================================================
# SINGLE GLOBAL INSTANCE
# ==========================================================

intelligence_orchestrator = IntelligenceOrchestrator()