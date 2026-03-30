# app/lab/explanation_engine.py


class ExplanationEngine:

    def generate(self, best, results):
        explanations = []

        if not results:
            return ["No strategies were generated."]

        # =============================
        # 🏆 BEST STRATEGY EXPLANATION
        # =============================
        name = best.get("name", "Unknown")
        score = best.get("final_score", best.get("score", 0))
        risk = best.get("risk", "unknown")
        confidence = best.get("confidence", 0.0)

        explanations.append(
            f"The best strategy is '{name}' with a score of {score:.2f}."
        )

        explanations.append(
            f"It has a '{risk}' risk profile with a confidence level of {confidence:.2f}."
        )

        # =============================
        # 📊 COMPARISON INSIGHT (FIXED)
        # =============================
        sorted_results = sorted(
            results,
            key=lambda x: x.get("final_score", x.get("score", 0)),
            reverse=True
        )

        if len(sorted_results) > 1:
            second = sorted_results[1]

            second_name = second.get("name", "Unknown")
            second_score = second.get("final_score", second.get("score", 0))

            explanations.append(
                f"It outperformed '{second_name}' by {(score - second_score):.2f} points."
            )

        # =============================
        # 🧠 STRATEGY INSIGHT
        # =============================
        if risk == "high":
            explanations.append(
                "This strategy is aggressive and benefits from high-risk, high-reward environments."
            )
        elif risk == "medium":
            explanations.append(
                "This strategy balances risk and reward, making it suitable for uncertain environments."
            )
        elif risk == "low":
            explanations.append(
                "This strategy is conservative and performs better in stable or low-risk conditions."
            )
        else:
            explanations.append(
                "This strategy adapts dynamically to the current environment."
            )

        return explanations


# ✅ instance
explanation_engine = ExplanationEngine()