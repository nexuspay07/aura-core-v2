class MarketIntelligenceEngine:

    def analyze(self, business_intent: str, scenario: dict):
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")

        pressure = self._market_pressure(market, budget)
        survival_strategy = self._survival_strategy(business_intent, budget, market)
        growth_angle = self._growth_angle(business_intent, budget, market)

        return {
            "market_pressure": pressure,
            "survival_strategy": survival_strategy,
            "growth_angle": growth_angle,
            "premium_insight": self._premium_insight(business_intent, budget, market)
        }

    def _market_pressure(self, market: str, budget: int):
        if market == "competitive" and budget <= 5000:
            return (
                "You are operating in a difficult environment: customers are price-sensitive, "
                "competition is high, and your budget is limited. This means you cannot win by "
                "spending more than competitors. You must win by being more specific, more trusted, "
                "and more valuable to a smaller audience."
            )

        if market == "competitive":
            return (
                "Competition is high, so growth will depend on differentiation, trust, and clear value. "
                "A generic offer will be ignored. Your business must communicate why customers should "
                "choose you instead of cheaper or more established competitors."
            )

        if market == "monopoly":
            return (
                "Competition is low, which gives you pricing power. The main risk is becoming too slow "
                "or too comfortable. You should focus on strong positioning and maximizing margins."
            )

        return (
            "Market conditions are uncertain. Customers are cautious, so your business should protect cash, "
            "validate demand early, and focus on clear value before scaling."
        )

    def _survival_strategy(self, business_intent: str, budget: int, market: str):
        if budget <= 5000:
            return (
                "Survival priority: avoid large fixed costs. Do not hire too early, do not overspend on ads, "
                "and do not build too many features. Use manual outreach, partnerships, referrals, and direct "
                "customer conversations before spending heavily."
            )

        if market == "competitive":
            return (
                "Survival priority: avoid blending in. Your business should specialize in one customer segment, "
                "build proof quickly, and use testimonials or case studies to increase trust."
            )

        return (
            "Survival priority: keep spending controlled while validating repeat demand. Growth should only happen "
            "after you see proof that customers are willing to return or refer others."
        )

    def _growth_angle(self, business_intent: str, budget: int, market: str):
        if business_intent == "pricing":
            return (
                "Do not simply lower prices. Instead, test value-based bundles: offer a basic option for price-sensitive "
                "customers and a higher-value option for customers who want better results."
            )

        if business_intent == "growth":
            return (
                "The best growth path is narrow targeting. Pick one customer group, solve one painful problem, "
                "and make your offer feel specifically built for them."
            )

        if business_intent == "cost":
            return (
                "Cut costs that do not directly create customers, retention, or product quality. Do not cut the parts "
                "that make the customer trust you."
            )

        if business_intent == "market_entry":
            return (
                "Enter the market through a small wedge. Do not launch broadly. Start with one niche, prove demand, "
                "then expand outward."
            )

        return (
            "Growth should come from focused execution: one offer, one customer segment, one measurable outcome."
        )

    def _premium_insight(self, business_intent: str, budget: int, market: str):
        if market == "competitive" and budget <= 5000:
            return (
                "The hidden advantage is speed of learning. Bigger competitors may have more money, but they often move slowly. "
                "Your advantage is testing faster, talking to customers directly, and adjusting before competitors notice."
            )

        return (
            "The key is not just choosing a strategy, but choosing the strategy that matches your constraints. "
            "A good business decision is one that survives bad conditions and still leaves room to grow."
        )


market_intelligence_engine = MarketIntelligenceEngine()