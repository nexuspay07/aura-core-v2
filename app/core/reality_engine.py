class RealityEngine:

    def analyze(self, business_intent: str, scenario: dict):
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")
        risk = scenario.get("risk", "medium")

        return {
            "reality_check": self._reality_check(budget, market),
            "brutal_truth": self._brutal_truth(business_intent, budget, market),
            "why_not_aggressive": self._why_not_aggressive(budget, market),
            "why_not_balanced": self._why_not_balanced(budget, market),
            "why_this_strategy_wins": self._why_this_strategy_wins(business_intent, budget, market, risk),
        }

    def _reality_check(self, budget: int, market: str):
        if market == "competitive" and budget <= 5000:
            return (
                f"With only ${budget}, you are not in a position to win by spending more. "
                "Competitors may already have trust, reviews, visibility, and stronger budgets. "
                "Your smartest move is to reduce waste, target narrowly, and learn faster than them."
            )

        if market == "competitive":
            return (
                "You are entering a market where customers already have options. "
                "If your offer does not clearly feel different, safer, or more valuable, "
                "customers will default to competitors."
            )

        return (
            "The main danger is assuming demand exists before proving it. "
            "Your first job is not growth — it is validation."
        )

    def _brutal_truth(self, business_intent: str, budget: int, market: str):
        if market == "competitive" and budget <= 5000:
            return (
                "Most small businesses fail here because they try to look big too early. "
                "They spend on ads, branding, or features before proving that real customers want the offer. "
                "You should act small, test fast, and protect cash."
            )

        if business_intent == "growth":
            return (
                "Growth without proof is dangerous. More attention does not mean more sales. "
                "If the offer is weak, scaling only exposes the weakness faster."
            )

        if business_intent == "pricing":
            return (
                "Lower pricing alone is not a strategy. If customers do not understand the value, "
                "a lower price can make the business look cheap instead of attractive."
            )

        return (
            "The uncomfortable truth is that the market does not reward effort. "
            "It rewards clear value, trust, timing, and execution."
        )

    def _why_not_aggressive(self, budget: int, market: str):
        if budget <= 5000:
            return (
                "Aggressive growth is too risky because your budget cannot absorb many mistakes. "
                "One bad ad campaign, wrong offer, or weak conversion test could waste too much of your capital."
            )

        if market == "competitive":
            return (
                "Aggressive growth can work, but in a competitive market it increases burn rate fast. "
                "Without strong proof, you may spend heavily just to educate customers for competitors."
            )

        return (
            "Aggressive execution may be unnecessary until demand is proven."
        )

    def _why_not_balanced(self, budget: int, market: str):
        if market == "competitive" and budget <= 5000:
            return (
                "Balanced strategy is better than aggressive, but it may still spread your effort too wide. "
                "With a small budget, focus beats balance. You need one narrow customer segment first."
            )

        return (
            "Balanced strategy is useful, but it should only be used after you know which customer segment responds best."
        )

    def _why_this_strategy_wins(self, business_intent: str, budget: int, market: str, risk: str):
        if market == "competitive" and budget <= 5000:
            return (
                "The niche-first strategy wins because it protects your money while giving you faster learning. "
                "Instead of trying to convince everyone, you focus on the smallest group most likely to care."
            )

        if market == "competitive":
            return (
                "Differentiation wins because customers need a clear reason to switch from existing options."
            )

        return (
            "Validation wins because it prevents you from scaling a weak idea."
        )


reality_engine = RealityEngine()