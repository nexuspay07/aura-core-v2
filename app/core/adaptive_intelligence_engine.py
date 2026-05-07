class AdaptiveIntelligenceEngine:

    def analyze(self, goal: str, scenario: dict):
        m = goal.lower()

        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")
        risk = scenario.get("risk", "medium")

        industry = self._detect_industry(m)
        stage = self._detect_stage(m)
        urgency = self._detect_urgency(m)

        return {
            "industry": industry,
            "business_stage": stage,
            "urgency": urgency,
            "adaptive_strategy": self._adaptive_strategy(industry, budget, market, stage),
            "customer_psychology": self._customer_psychology(industry, market),
            "dominant_advantage": self._dominant_advantage(industry, budget, market),
            "execution_style": self._execution_style(budget, risk, urgency),
            "growth_style": self._growth_style(industry, budget, market),
            "communication_strategy": self._communication_strategy(industry, market),
            "avoid_this": self._avoid_this(industry, budget, market),
        }

    def _detect_industry(self, m: str):
        if any(x in m for x in ["restaurant", "food", "cafe", "bakery", "shawarma", "chicken", "pizza"]):
            return "food_service"

        if any(x in m for x in ["clothing", "fashion", "brand", "shirt", "hoodie", "shoes"]):
            return "fashion"

        if any(x in m for x in ["ai", "software", "app", "saas", "tech", "platform"]):
            return "technology"

        if any(x in m for x in ["cleaning", "barber", "salon", "repair", "plumbing", "service"]):
            return "local_service"

        if any(x in m for x in ["course", "tutor", "school", "education", "training"]):
            return "education"

        return "general_business"

    def _detect_stage(self, m: str):
        if any(x in m for x in ["idea", "start", "starting", "open", "launch", "new business"]):
            return "early_stage"

        if any(x in m for x in ["grow", "scale", "more customers", "increase sales"]):
            return "growth_stage"

        if any(x in m for x in ["struggling", "losing money", "not selling", "low sales"]):
            return "survival_stage"

        return "unknown_stage"

    def _detect_urgency(self, m: str):
        if any(x in m for x in ["urgent", "quick", "fast", "asap", "immediately", "now"]):
            return "high"

        return "normal"

    def _adaptive_strategy(self, industry: str, budget: int, market: str, stage: str):
        if industry == "food_service":
            return (
                "Focus on trust, repeat customers, and local demand before expansion. "
                "Food businesses win through consistency, location fit, customer experience, and repeat buying."
            )

        if industry == "fashion":
            return (
                "Focus on identity and perception. Fashion customers buy meaning, style, and belonging — not only products."
            )

        if industry == "technology":
            return (
                "Prioritize speed of learning. Build a simple version, test quickly, and improve based on real user behavior."
            )

        if industry == "local_service":
            return (
                "Win through trust, referrals, reviews, and reliability. Local service businesses grow when customers feel safe choosing you."
            )

        if industry == "education":
            return (
                "Win through credibility and clear outcomes. People pay when they believe your teaching can produce measurable improvement."
            )

        if market == "competitive" and budget <= 5000:
            return (
                "Use a narrow-entry strategy: pick one customer group, one painful problem, and one clear promise before spending broadly."
            )

        return (
            "Use a validation-first strategy: prove demand, then scale only what works."
        )

    def _customer_psychology(self, industry: str, market: str):
        if industry == "food_service":
            return (
                "Customers decide based on taste, convenience, cleanliness, reviews, location, and whether they believe the food will be consistent."
            )

        if industry == "fashion":
            return (
                "Customers decide based on style, identity, social proof, perceived quality, and how the brand makes them feel."
            )

        if industry == "technology":
            return (
                "Users decide based on usefulness, speed, simplicity, trust, and whether the product saves time or creates advantage."
            )

        if industry == "local_service":
            return (
                "Customers decide based on trust, reviews, responsiveness, pricing clarity, and fear of choosing the wrong provider."
            )

        if industry == "education":
            return (
                "Customers decide based on credibility, proof of results, simplicity, and confidence that they will improve."
            )

        if market == "competitive":
            return (
                "Customers already have options, so they need a clear reason to trust you instead of choosing a known competitor."
            )

        return (
            "Customers need clarity, trust, and a simple reason to act."
        )

    def _dominant_advantage(self, industry: str, budget: int, market: str):
        if budget <= 5000:
            return (
                "Your advantage is not money. Your advantage is speed, focus, direct customer conversations, and fast adjustment."
            )

        if industry == "technology":
            return (
                "Your advantage is iteration speed — learning faster than competitors and improving the product quickly."
            )

        if industry == "local_service":
            return (
                "Your advantage is personal trust and better customer experience."
            )

        if industry == "fashion":
            return (
                "Your advantage is brand identity and community, not just price."
            )

        return (
            "Your advantage is focus and execution discipline."
        )

    def _execution_style(self, budget: int, risk: str, urgency: str):
        if urgency == "high":
            return (
                "Move fast, but use small controlled tests. Do not rush into expensive commitments."
            )

        if budget <= 5000:
            return (
                "Lean execution: manual testing, low spend, customer conversations, and proof before scaling."
            )

        if risk == "high":
            return (
                "Aggressive testing is possible, but every experiment must have clear limits and success metrics."
            )

        return (
            "Balanced execution: test, measure, improve, then scale."
        )

    def _growth_style(self, industry: str, budget: int, market: str):
        if industry == "food_service":
            return (
                "Growth should come from repeat customers, local awareness, reviews, and simple offers people can recommend."
            )

        if industry == "fashion":
            return (
                "Growth should come from content, identity, social proof, and community-driven demand."
            )

        if industry == "technology":
            return (
                "Growth should come from solving one painful use case extremely well before expanding features."
            )

        if industry == "local_service":
            return (
                "Growth should come from reviews, referrals, local SEO, and fast response time."
            )

        if budget <= 5000:
            return (
                "Growth should be organic first: direct outreach, partnerships, referrals, and niche communities."
            )

        return (
            "Growth should be channel-tested: try small campaigns, measure results, and scale the best channel."
        )

    def _communication_strategy(self, industry: str, market: str):
        if industry == "food_service":
            return (
                "Communicate freshness, taste, trust, convenience, and why people should return."
            )

        if industry == "fashion":
            return (
                "Communicate identity, lifestyle, quality, and what the brand says about the customer."
            )

        if industry == "technology":
            return (
                "Communicate the painful problem, the time saved, and the advantage users gain."
            )

        if industry == "local_service":
            return (
                "Communicate reliability, proof, reviews, clear pricing, and fast response."
            )

        if market == "competitive":
            return (
                "Communicate why you are different, who you are best for, and why customers can trust you."
            )

        return (
            "Communicate a clear promise, simple benefit, and low-risk reason to try."
        )

    def _avoid_this(self, industry: str, budget: int, market: str):
        if budget <= 5000:
            return (
                "Avoid large upfront spending, broad ads, unnecessary branding, hiring too early, or building too much before demand is proven."
            )

        if market == "competitive":
            return (
                "Avoid copying competitors without a clear difference. Similar offers get ignored."
            )

        return (
            "Avoid scaling before you know what customers actually respond to."
        )


adaptive_intelligence_engine = AdaptiveIntelligenceEngine()