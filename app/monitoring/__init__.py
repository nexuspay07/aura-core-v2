# app/monitoring/monitoring_engine.py

import time
import psutil


class MonitoringEngine:

    def __init__(self):
        self.metrics = []
        self.errors = []
        self.events = []

    # -------------------
    # System Metrics
    # -------------------
    def collect_system_metrics(self):

        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "timestamp": time.time()
        }

        self.metrics.append(metrics)

        print(f"[MONITORING] Metrics: {metrics}")

        return metrics

    # -------------------
    # Cognitive Events
    # -------------------
    def log_event(self, event_type, data=None):

        event = {
            "type": event_type,
            "data": data or {},
            "timestamp": time.time()
        }

        self.events.append(event)

        print(f"[MONITORING] Event: {event_type}")

    # -------------------
    # Error Tracking
    # -------------------
    def log_error(self, error_message):

        error = {
            "error": str(error_message),
            "timestamp": time.time()
        }

        self.errors.append(error)

        print(f"[MONITORING] ERROR: {error_message}")

    # -------------------
    # Stats
    # -------------------
    def get_stats(self):

        return {
            "metrics_count": len(self.metrics),
            "events_count": len(self.events),
            "errors_count": len(self.errors)
        }


# Singleton
monitoring_engine = MonitoringEngine()