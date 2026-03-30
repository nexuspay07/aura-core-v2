class DecisionEngine:

    def __init__(self):
        self.wait_thresholds = {
            "low": 30,
            "moderate": 60,
            "high": 90
        }

        # Governance constraints
        self.max_safe_load = 0.85
        self.max_source_load = 0.70
        self.min_staff_per_department = 1

    # ---------------------------
    # PUBLIC ENTRY POINT
    # ---------------------------
    def evaluate_department(self, department_state):
        forecast = self._forecast_30_min(department_state)
        risk_level = self._classify_risk(forecast["predicted_awt"])

        scenarios = self._simulate_interventions(department_state)
        best_action = self._select_best_action(scenarios)

        return {
            "risk_level": risk_level,
            "forecast": forecast,
            "recommended_action": best_action,
            "scenarios_evaluated": scenarios
        }

    # ---------------------------
    # 1. FORECASTING
    # ---------------------------
    def _forecast_30_min(self, state):
        arrival_rate = state["arrival_rate"]
        staff = state["staff"]
        service_rate = state["service_rate"]
        queue_now = state["queue_length"]

        capacity_rate = staff * service_rate

        arrivals_30 = arrival_rate * 0.5
        processed_30 = capacity_rate * 0.5

        queue_future = max(0, queue_now + arrivals_30 - processed_30)

        predicted_awt = 0
        if capacity_rate > 0:
            predicted_awt = (queue_future / capacity_rate) * 60

        return {
            "queue_future": queue_future,
            "predicted_awt": predicted_awt
        }

    # ---------------------------
    # 2. RISK CLASSIFICATION
    # ---------------------------
    def _classify_risk(self, predicted_awt):
        if predicted_awt < self.wait_thresholds["low"]:
            return "LOW"
        elif predicted_awt < self.wait_thresholds["moderate"]:
            return "MODERATE"
        elif predicted_awt < self.wait_thresholds["high"]:
            return "HIGH"
        else:
            return "CRITICAL"

    # ---------------------------
    # 3. SCENARIO SIMULATION
    # ---------------------------
    def _simulate_interventions(self, state):
        scenarios = []

        # Maintain current staffing
        maintain_forecast = self._forecast_30_min(state)
        scenarios.append({
            "action": "maintain",
            "forecast": maintain_forecast
        })

        # Add one staff (if allowed)
        if state["staff"] >= self.min_staff_per_department:
            new_state = state.copy()
            new_state["staff"] += 1
            add_staff_forecast = self._forecast_30_min(new_state)

            scenarios.append({
                "action": "add_staff",
                "forecast": add_staff_forecast
            })

        return scenarios

    # ---------------------------
    # 4. ACTION SELECTION
    # ---------------------------
    def _select_best_action(self, scenarios):
        best = None
        lowest_awt = float("inf")

        for scenario in scenarios:
            awt = scenario["forecast"]["predicted_awt"]

            if awt < lowest_awt:
                lowest_awt = awt
                best = scenario

        return best
    
    # GLOBAL INSTANCE
decision_engine = DecisionEngine()