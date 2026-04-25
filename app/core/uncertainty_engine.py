class UncertaintyEngine:
    def __init__(self):
        print("[UNCERTAINTY ENGINE] Initialized")

    def estimate_probability(self, prediction: dict):
        """
        Estimate probability of the predicted outcome using confidence
        and risk-related factors instead of randomness.
        """
        confidence = prediction.get("confidence_used", 0.7)
        risk_penalty = prediction.get("risk_penalty", 0.3)
        world_factors = prediction.get("world_factors", {})

        competition = world_factors.get("competition", 0.5)
        risk_level = world_factors.get("risk_level", 0.5)

        probability = confidence - (risk_penalty * 0.2) - (competition * 0.1) - (risk_level * 0.1)
        probability = max(0.05, min(0.95, probability))

        prediction["probability"] = round(probability, 2)
        return prediction

    def calculate_expected_value(self, prediction: dict):
        predicted_score = prediction.get("predicted_score", 0)
        probability = prediction.get("probability", 1)

        expected_value = predicted_score * probability
        prediction["expected_value"] = round(expected_value, 2)

        return prediction

    def evaluate_risk(self, prediction: dict):
        probability = prediction.get("probability", 1)
        uncertainty_risk = 1 - probability

        prediction["uncertainty_risk"] = round(uncertainty_risk, 2)
        return prediction

    def add_uncertainty_band(self, prediction: dict):
        predicted_score = prediction.get("predicted_score", 0)
        uncertainty_risk = prediction.get("uncertainty_risk", 0.2)

        spread = predicted_score * uncertainty_risk * 0.5

        prediction["prediction_range"] = {
            "low": round(predicted_score - spread, 2),
            "high": round(predicted_score + spread, 2)
        }

        return prediction

    def rank_uncertain_predictions(self, predictions: list):
        evaluated = []

        for p in predictions:
            p = self.estimate_probability(p)
            p = self.calculate_expected_value(p)
            p = self.evaluate_risk(p)
            p = self.add_uncertainty_band(p)
            evaluated.append(p)

        ranked = sorted(
            evaluated,
            key=lambda x: x["expected_value"],
            reverse=True
        )

        print("[UNCERTAINTY ENGINE] Predictions ranked with uncertainty")
        return ranked

    def enrich_predictions(self, predictions: list):
        """
        Adds uncertainty evaluation without changing original ranking logic elsewhere.
        """
        return self.rank_uncertain_predictions(predictions)


uncertainty_engine = UncertaintyEngine()