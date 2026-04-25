class LearningEngine:

    def __init__(self):
        self.learning_rate = 0.2

    # ==========================
    # 🧠 BUILD CONTEXT KEY
    # ==========================
    def build_context_key(self, strategy_name, scenario):
        risk = scenario.get("risk_tolerance", 0.5)
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")

        risk_level = "high_risk" if risk > 0.6 else "low_risk"
        budget_level = "high_budget" if budget > 8000 else "low_budget"

        return f"{strategy_name}|{risk_level}|{budget_level}|{market}"

    # ==========================
    # 🧠 LEARN FROM HISTORY
    # ==========================
    async def learn(self, username, history_engine):
        history = await history_engine.get(username)

        if not history:
            return {}

        context_scores = {}
        context_counts = {}

        for record in history:
            scenario = record.get("scenario", {})
            result = record.get("result", {})
            strategies = result.get("results", [])

            for strat in strategies:
                name = strat.get("name")
                score = strat.get("final_score", strat.get("score", 0))

                key = self.build_context_key(name, scenario)

                if key not in context_scores:
                    context_scores[key] = 0
                    context_counts[key] = 0

                context_scores[key] += score
                context_counts[key] += 1

        learned_patterns = {}

        for key in context_scores:
            avg_score = context_scores[key] / context_counts[key]
            learned_patterns[key] = round(avg_score * self.learning_rate, 4)

        return learned_patterns

    # ==========================
    # ⚡ APPLY CONTEXT LEARNING
    # ==========================
    def apply_learning(self, strategies, scenario, patterns):
        for strat in strategies:
            key = self.build_context_key(strat["name"], scenario)

            bonus = patterns.get(key, 0)

            strat["learning_bonus"] = round(bonus, 4)
            strat["learning_context_key"] = key

            if bonus:
                strat["score"] = strat.get("score", 0) + bonus

        return strategies


learning_engine = LearningEngine()