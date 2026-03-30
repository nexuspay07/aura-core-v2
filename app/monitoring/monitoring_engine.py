# app/monitoring/monitoring_engine.py

import psutil
import time

class MonitoringEngine:
    def __init__(self):
        self.logs = []

    def collect_system_metrics(self):
        # Example: CPU, memory, time
        metrics = {
            "cpu": psutil.cpu_percent(interval=0.1),
            "memory": psutil.virtual_memory().percent,
            "timestamp": time.time()
        }
        self.logs.append({"type": "metrics", "data": metrics})
        return metrics

    def log_event(self, event_name, data=None):
        entry = {
            "type": "event",
            "event": event_name,
            "data": data,
            "timestamp": time.time()
        }
        self.logs.append(entry)
        print(f"[MONITORING] Event logged: {event_name}")
        return entry

    def log_error(self, error):
        entry = {
            "type": "error",
            "error": str(error),
            "timestamp": time.time()
        }
        self.logs.append(entry)
        print(f"[MONITORING] ERROR: {error}")
        return entry

# Global instance
monitoring_engine = MonitoringEngine()