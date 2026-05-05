import json
import os
from datetime import datetime


class PaymentTracker:
    def __init__(self):
        self.file_path = "payment_events.json"

    def log_event(self, event_type: str, data: dict | None = None):
        event = {
            "event_type": event_type,
            "data": data or {},
            "created_at": datetime.utcnow().isoformat()
        }

        events = self._load_events()
        events.append(event)

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)

        return event

    def get_stats(self):
        events = self._load_events()

        unlock_clicks = len([e for e in events if e["event_type"] == "unlock_clicked"])
        checkout_created = len([e for e in events if e["event_type"] == "checkout_created"])
        payment_success = len([e for e in events if e["event_type"] == "payment_success"])

        revenue = payment_success * 5

        return {
            "unlock_clicks": unlock_clicks,
            "checkout_created": checkout_created,
            "payment_success": payment_success,
            "estimated_revenue": revenue,
            "events": events[-20:]
        }

    def _load_events(self):
        if not os.path.exists(self.file_path):
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


payment_tracker = PaymentTracker()