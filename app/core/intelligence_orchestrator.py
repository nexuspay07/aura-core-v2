from datetime import datetime


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


intelligence_orchestrator = IntelligenceOrchestrator()