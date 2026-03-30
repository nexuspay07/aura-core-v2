# app/core/uncertainty_engine.py

import random


class UncertaintyEngine:

    def __init__(self):
        print("[UNCERTAINTY ENGINE] Initialized")

    def estimate_probability(self, prediction):
        """
        Estimate probability/confidence for a predicted outcome.
        """

        # simple baseline probability
        probability = random.uniform(0.6, 0.95)

        prediction["probability"] = probability

        return prediction

    def calculate_expected_value(self, prediction):

        score = prediction.get("score", 0)
        probability = prediction.get("probability", 1)

        expected_value = score * probability

        prediction["expected_value"] = expected_value

        return prediction

    def evaluate_risk(self, prediction):

        probability = prediction.get("probability", 1)

        risk = 1 - probability

        prediction["risk"] = risk

        return prediction

    def rank_uncertain_predictions(self, predictions):

        evaluated = []

        for p in predictions:

            p = self.estimate_probability(p)
            p = self.calculate_expected_value(p)
            p = self.evaluate_risk(p)

            evaluated.append(p)

        ranked = sorted(
            evaluated,
            key=lambda x: x["expected_value"],
            reverse=True
        )

        print("[UNCERTAINTY ENGINE] Predictions ranked with uncertainty")

        return ranked


uncertainty_engine = UncertaintyEngine()