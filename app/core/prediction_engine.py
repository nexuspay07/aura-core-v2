class PredictionEngine:

    def predict_outcome(self, intent: str, strategy: str, scenario: dict):
        risk = scenario.get("risk", "medium")

        # Normalize intent
        intent = intent.lower()

        # ==========================
        # PRICING
        # ==========================
        if "pricing" in intent:
            return {
                "impact": "Lower pricing may increase conversions by 20–30%",
                "tradeoff": "Lower margins in early stages",
                "timeframe": "Short-term (1–4 weeks)",
                "confidence": 0.7
            }

        # ==========================
        # GROWTH
        # ==========================
        if "growth" in intent:
            return {
                "impact": "Focused growth strategy can improve efficiency by 2–3x",
                "tradeoff": "Slower expansion initially while testing",
                "timeframe": "Medium-term (1–3 months)",
                "confidence": 0.65
            }

        # ==========================
        # COST
        # ==========================
        if "cost" in intent or "expenses" in intent:
            return {
                "impact": "Reducing expenses can extend runway by 20–40%",
                "tradeoff": "May reduce operational capacity",
                "timeframe": "Immediate to short-term",
                "confidence": 0.75
            }

        # ==========================
        # GENERAL BUSINESS
        # ==========================
        if "business" in intent:
            return {
                "impact": "Structured execution can increase success probability significantly",
                "tradeoff": "Requires patience and disciplined testing",
                "timeframe": "Medium-term (1–3 months)",
                "confidence": 0.6
            }

        # ==========================
        # DEFAULT FALLBACK
        # ==========================
        return {
            "impact": "This decision may improve stability and reduce risk",
            "tradeoff": "May limit aggressive growth opportunities",
            "timeframe": "Medium-term",
            "confidence": 0.5
        }


prediction_engine = PredictionEngine()