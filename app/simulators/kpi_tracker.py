class KPITracker:

    def __init__(self):

        self.history = []

        print("[KPI TRACKER] Initialized")

    # ---------------------------
    # Record hospital metrics
    # ---------------------------
    def record(self, state):

        kpi = {
            "patients": state["patients"],
            "staff": state["staff"],
            "wait_time": state["wait_time"]
        }

        self.history.append(kpi)

        if len(self.history) > 100:
            self.history.pop(0)

        return kpi

    # ---------------------------
    # Get latest KPI
    # ---------------------------
    def latest(self):

        if not self.history:
            return None

        return self.history[-1]

    # ---------------------------
    # KPI evaluation
    # ---------------------------
    def evaluate(self):

        if not self.history:
            return {"status": "no_data"}

        latest = self.latest()

        if latest["wait_time"] > 30:
            status = "overloaded"

        elif latest["patients"] > 80:
            status = "near_capacity"

        else:
            status = "stable"

        return {
            "status": status,
            "latest": latest
        }


# GLOBAL INSTANCE
kpi_tracker = KPITracker()