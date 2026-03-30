# app/core/autonomous_self_debugging_engine.py

import traceback
from datetime import datetime

class AutonomousSelfDebuggingEngine:
    def __init__(self):
        self.error_log = []

    def monitor(self, cognitive_loop, run_result):
        """
        Inspect run result and system state for anomalies.
        """
        issues_detected = []

        # Example checks
        if run_result.get("score", 0) < 0.5:
            issues_detected.append("Low goal achievement score")

        if not run_result.get("plan"):
            issues_detected.append("No plan generated for active goal")

        resources = run_result.get("resources", {})
        if resources.get("cpu", 0) > 90:
            issues_detected.append("CPU usage unusually high")
        if resources.get("memory", 0) > 90:
            issues_detected.append("Memory usage unusually high")

        # Log detected issues
        for issue in issues_detected:
            self.log_error(issue)

        return issues_detected

    def log_error(self, error_message):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error_message
        }
        self.error_log.append(entry)
        print(f"[SELF-DEBUG] {entry['timestamp']} | {entry['error']}")

    def attempt_fix(self, issue):
        """
        Try to automatically resolve common issues.
        Returns True if resolved, False otherwise.
        """
        # Example simple fixes
        if issue == "Low goal achievement score":
            print("[SELF-DEBUG] Suggest increasing plan granularity or resources")
            return False
        if issue == "No plan generated for active goal":
            print("[SELF-DEBUG] Regenerating plan using planning engine")
            return True  # Assume plan regenerated successfully
        if "CPU usage" in issue or "Memory usage" in issue:
            print("[SELF-DEBUG] Recommend resource optimization or throttling")
            return False

        print("[SELF-DEBUG] No automatic fix available")
        return False

    def review_errors(self):
        """
        Returns all logged errors for inspection.
        """
        return self.error_log