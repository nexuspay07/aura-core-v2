class VisualIntelligenceEngine:

    def analyze(self, decision_brief: dict):
        confidence = decision_brief.get("confidence", 0.65)
        risk_text = (decision_brief.get("main_risk") or "").lower()
        market_pressure = (decision_brief.get("market_pressure") or "").lower()

        risk_score = self._risk_score(risk_text)
        market_score = self._market_pressure_score(market_pressure)
        execution_score = self._execution_score(confidence, risk_score)
        decision_strength = self._decision_strength(confidence, risk_score, market_score)

        return {
            "confidence_percent": int(confidence * 100),
            "risk_score": risk_score,
            "risk_label": self._risk_label(risk_score),
            "market_pressure_score": market_score,
            "market_pressure_label": self._pressure_label(market_score),
            "execution_difficulty": execution_score,
            "execution_label": self._execution_label(execution_score),
            "decision_strength": decision_strength,
            "decision_strength_label": self._strength_label(decision_strength),
            "competitor_matrix": self._competitor_matrix(),
            "key_metrics": {
                "trust_gap": "High",
                "cash_protection": "Important",
                "speed_advantage": "Strong",
                "validation_need": "Very high"
            }
        }

    def _risk_score(self, text: str):
        if "too fast" in text or "high" in text:
            return 75
        if "too slowly" in text:
            return 45
        return 60

    def _market_pressure_score(self, text: str):
        if "competitive" in text or "competition is high" in text:
            return 82
        if "uncertain" in text:
            return 65
        return 50

    def _execution_score(self, confidence: float, risk_score: int):
        return max(20, min(95, int((risk_score * 0.6) + ((1 - confidence) * 100 * 0.4))))

    def _decision_strength(self, confidence: float, risk_score: int, market_score: int):
        return max(20, min(95, int((confidence * 100 * 0.6) + ((100 - risk_score) * 0.25) + ((100 - market_score) * 0.15))))

    def _risk_label(self, score: int):
        if score >= 70:
            return "High Risk"
        if score >= 45:
            return "Medium Risk"
        return "Low Risk"

    def _pressure_label(self, score: int):
        if score >= 75:
            return "Heavy Market Pressure"
        if score >= 55:
            return "Moderate Market Pressure"
        return "Low Market Pressure"

    def _execution_label(self, score: int):
        if score >= 70:
            return "Hard Execution"
        if score >= 45:
            return "Moderate Execution"
        return "Easy Execution"

    def _strength_label(self, score: int):
        if score >= 75:
            return "Strong Decision"
        if score >= 55:
            return "Balanced Decision"
        return "Weak / Needs Validation"

    def _competitor_matrix(self):
        return {
            "you": {
                "trust": "Low–Medium",
                "speed": "High",
                "brand": "Low",
                "flexibility": "High"
            },
            "competitors": {
                "trust": "High",
                "speed": "Medium",
                "brand": "High",
                "flexibility": "Low–Medium"
            }
        }


visual_intelligence_engine = VisualIntelligenceEngine()