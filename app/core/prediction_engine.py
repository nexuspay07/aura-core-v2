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

    def predict_outcome(self, intent: str, strategy: str, scenario: dict):
        intent = intent.lower()

        if "pricing" in intent:
            return {
                "impact": "Lower pricing may increase conversions by 20–30%",
                "tradeoff": "Lower margins in early stages",
                "timeframe": "Short-term (1–4 weeks)",
                "confidence": 0.7
            }

        if "growth" in intent:
            return {
                "impact": "Focused growth strategy can improve efficiency by 2–3x",
                "tradeoff": "Slower expansion initially while testing",
                "timeframe": "Medium-term (1–3 months)",
                "confidence": 0.65
            }

        if "cost" in intent or "expenses" in intent:
            return {
                "impact": "Reducing expenses can extend runway by 20–40%",
                "tradeoff": "May reduce operational capacity",
                "timeframe": "Immediate to short-term",
                "confidence": 0.75
            }

        if "hiring" in intent:
            return {
                "impact": "Delaying hiring until demand is proven can protect cash flow",
                "tradeoff": "You may grow slower if workload increases quickly",
                "timeframe": "Short to medium-term",
                "confidence": 0.65
            }

        if "market" in intent:
            return {
                "impact": "Starting with a narrow niche can improve early traction",
                "tradeoff": "Limits your initial audience size",
                "timeframe": "Medium-term (1–3 months)",
                "confidence": 0.6
            }

        return {
            "impact": "This decision may improve stability and reduce risk",
            "tradeoff": "May limit aggressive growth opportunities",
            "timeframe": "Medium-term",
            "confidence": 0.5
        }


prediction_engine = PredictionEngine()