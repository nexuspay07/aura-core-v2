class PredictionEngine:

    def simulate_strategy(self, strategy, world_state):
        predicted_score = strategy.get("final_score", strategy.get("score", 1))

        return {
            "strategy": strategy.get("name", "Unknown"),
            "predicted_score": predicted_score,
            "probability": strategy.get("confidence", 0.7),
            "expected_value": predicted_score * strategy.get("confidence", 0.7),
            "uncertainty_risk": 1 - strategy.get("confidence", 0.7),
            "prediction_range": {
                "low": round(predicted_score * 0.8, 2),
                "high": round(predicted_score * 1.2, 2)
            }
        }

    def simulate_multiple(self, strategies, world_state):
        return [
            self.simulate_strategy(strategy, world_state)
            for strategy in strategies
        ]
    
    def get_market_context():
     return {
        "economy": "high inflation",
        "consumer_behavior": "price sensitive",
        "risk_level": "high uncertainty",
        "trend": "reduced discretionary spending"
    }

    def predict_outcome(self, intent: str, strategy: str, scenario: dict):
        intent = intent.lower()

        risk = scenario.get("risk", "medium")
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")

        # --------------------------
        # Adjust multipliers
        # --------------------------
        budget_factor = 1.0
        if budget < 5000:
            budget_factor = 0.8
        elif budget > 30000:
            budget_factor = 1.2

        risk_factor = 1.0
        if risk == "low":
            risk_factor = 0.85
        elif risk == "high":
            risk_factor = 1.15

        market_factor = 1.0
        if market == "competitive":
            market_factor = 0.8
        elif market == "monopoly":
            market_factor = 1.25

        final_factor = budget_factor * risk_factor * market_factor

        # --------------------------
        # PRICING
        # --------------------------
        if "pricing" in intent:
            base_low, base_high = 20, 30

            low = round(base_low * final_factor)
            high = round(base_high * final_factor)

            return {
                "impact": f"Expected conversion increase ~{low}–{high}%",
                "tradeoff": "Lower margins in early stages",
                "timeframe": "Short-term (1–4 weeks)",
                "confidence": 0.7,
                "context_note": f"Based on your budget (${budget}) and {market} market conditions"
            }

        # --------------------------
        # GROWTH
        # --------------------------
        if "growth" in intent:
            base_low, base_high = 2, 3

            low = round(base_low * final_factor, 1)
            high = round(base_high * final_factor, 1)

            return {
                "impact": f"Growth efficiency improvement ~{low}–{high}x",
                "tradeoff": "Slower early scaling while testing",
                "timeframe": "Medium-term (1–3 months)",
                "confidence": 0.65,
                "context_note": f"Adjusted for budget ${budget} and {market} competition"
            }

        # --------------------------
        # COST
        # --------------------------
        if "cost" in intent or "expenses" in intent:
            base_low, base_high = 20, 40

            low = round(base_low * final_factor)
            high = round(base_high * final_factor)

            return {
                "impact": f"Runway extension ~{low}–{high}%",
                "tradeoff": "Reduced operational capacity",
                "timeframe": "Immediate",
                "confidence": 0.75,
                "context_note": f"Based on current cost sensitivity and budget ${budget}"
            }

        # --------------------------
        # DEFAULT
        # --------------------------
        return {
            "impact": "Moderate improvement expected depending on execution",
            "tradeoff": "Balanced risk vs reward",
            "timeframe": "Medium-term",
            "confidence": 0.6,
            "context_note": f"General estimate for {market} conditions"
        }


prediction_engine = PredictionEngine()