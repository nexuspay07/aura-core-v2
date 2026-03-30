from datetime import datetime


class IntelligenceOrchestrator:

    def __init__(self):
        self.total_requests = 0
        self.last_event = None

    def process_event(self, event: dict):
        """
        Main processing entry for cognitive engine
        """

        self.total_requests += 1

        self.last_event = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat()
        }

        print(f"[INTELLIGENCE] Processed event #{self.total_requests}")

        return {
            "processed": True,
            "event": event,
            "timestamp": self.last_event["timestamp"],
            "total_requests": self.total_requests
        }

    def status(self):

        return {
            "total_requests": self.total_requests,
            "last_event": self.last_event
        }


# global singleton
intelligence_orchestrator = IntelligenceOrchestrator()