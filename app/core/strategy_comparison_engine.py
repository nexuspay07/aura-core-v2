class StrategyComparisonEngine:

    def compare(self, intent: str, scenario: dict):
        strategies = [
            {
                "name": "Conservative",
                "style": "safe",
                "base_score": 0.65,
                "risk": "low"
            },
            {
                "name": "Balanced",
                "style": "steady",
                "base_score": 0.75,
                "risk": "medium"
            },
            {
                "name": "Aggressive",
                "style": "fast",
                "base_score": 0.85,
                "risk": "high"
            }
        ]

        market = scenario.get("market", "normal")
        budget = scenario.get("budget", 10000)

        results = []

        for strategy in strategies:
            score = strategy["base_score"]

            if market == "competitive" and strategy["name"] == "Aggressive":
                score -= 0.15

            if market == "competitive" and strategy["name"] == "Balanced":
                score += 0.05

            if budget <= 5000 and strategy["name"] == "Conservative":
                score += 0.10

            if budget <= 5000 and strategy["name"] == "Aggressive":
                score -= 0.20

            if budget >= 30000 and strategy["name"] == "Aggressive":
                score += 0.10

            score = max(0.1, min(score, 0.95))

            results.append({
                "strategy": strategy["name"],
                "risk": strategy["risk"],
                "score": round(score, 2),
                "reason": self._reason(strategy["name"], market, budget)
            })

        best = max(results, key=lambda x: x["score"])

        return {
            "best_strategy": best,
            "comparisons": results
        }

    def _reason(self, strategy_name: str, market: str, budget: int):
        if strategy_name == "Conservative":
            if budget <= 5000:
                return "Best for protecting limited cash while testing demand."
            return "Safer, but may grow slower."

        if strategy_name == "Balanced":
            if market == "competitive":
                return "Strong fit for competitive markets because it balances testing and growth."
            return "Good middle path between growth and risk."

        if strategy_name == "Aggressive":
            if budget <= 5000:
                return "Risky with a small budget because mistakes become expensive."
            if market == "competitive":
                return "Can grow fast, but competition increases the chance of wasted spend."
            return "Best when speed matters and resources are available."

        return "General strategy option."


strategy_comparison_engine = StrategyComparisonEngine()