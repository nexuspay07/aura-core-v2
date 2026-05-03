class DecisionDepthEngine:

    def analyze(self, business_intent: str, scenario: dict):
        budget = scenario.get("budget", 10000)
        market = scenario.get("market", "normal")
        risk = scenario.get("risk", "medium")

        return {
            "personalized_reality": self._personalized_reality(budget, market),
            "consequence_simulation": self._consequence_simulation(business_intent, budget, market),
            "competitor_threat": self._competitor_threat(market, budget),
            "hidden_opportunity": self._hidden_opportunity(market, budget),
            "failure_triggers": self._failure_triggers(business_intent),
            "numbers_to_watch": self._numbers_to_watch(business_intent, budget),
        }

    def _personalized_reality(self, budget: int, market: str):
        if market == "competitive" and budget <= 5000:
            return (
                f"With a ${budget} budget in a competitive market, you cannot win by outspending competitors. "
                "Your best advantage is speed, focus, and trust. You need to choose one narrow customer group, "
                "prove value quickly, and avoid wasting money on broad marketing."
            )

        if market == "competitive":
            return (
                f"With a ${budget} budget in a competitive market, your success depends on differentiation. "
                "Customers already have options, so your offer must feel more specific, safer, or more valuable."
            )

        return (
            f"With a ${budget} budget, your main goal is to validate demand before scaling. "
            "Do not expand until you see proof that customers actually respond."
        )

    def _consequence_simulation(self, business_intent: str, budget: int, market: str):
        if market == "competitive" and budget <= 5000:
            return {
                "week_1": "Expect slow traction at first. Focus on customer conversations, niche testing, and offer clarity.",
                "week_2": "You should start seeing early signals: replies, clicks, small sales, or objections.",
                "week_3": "Double down only on the message or offer that gets the strongest response.",
                "week_4": "If results are weak, narrow the niche or change the offer before spending more.",
            }

        return {
            "week_1": "Test the offer with a small audience.",
            "week_2": "Measure which message creates the most response.",
            "week_3": "Improve the offer based on feedback.",
            "week_4": "Scale only the strategy with proof."
        }

    def _competitor_threat(self, market: str, budget: int):
        if market == "competitive":
            return (
                "Your biggest threat is not only price. It is trust. Competitors may already have reviews, reputation, "
                "better visibility, or stronger brand familiarity. If you do not build proof quickly, customers may choose "
                "the safer known option."
            )

        return (
            "Your biggest threat is slow execution. If you delay testing, another business can enter faster and capture attention."
        )

    def _hidden_opportunity(self, market: str, budget: int):
        if market == "competitive" and budget <= 5000:
            return (
                "Your hidden opportunity is speed of learning. Bigger competitors may have more money, but they often move slowly. "
                "You can talk to customers directly, test offers quickly, and adapt faster than larger businesses."
            )

        if market == "competitive":
            return (
                "Your hidden opportunity is specialization. Most competitors try to appeal to everyone. You can win by becoming "
                "the obvious choice for one specific customer segment."
            )

        return (
            "Your hidden opportunity is early positioning. If demand exists and competition is low, you can define the category before others enter."
        )

    def _failure_triggers(self, business_intent: str):
        if business_intent == "pricing":
            return [
                "People show interest but do not buy",
                "Customers say the price feels unclear or risky",
                "Lowering the price increases attention but not sales"
            ]

        if business_intent == "growth":
            return [
                "Customer acquisition cost rises without more sales",
                "People engage but do not convert",
                "You are spending more time marketing than improving the offer"
            ]

        return [
            "No clear customer response after testing",
            "You cannot explain why customers should choose you",
            "You are spending money before validating demand"
        ]

    def _numbers_to_watch(self, business_intent: str, budget: int):
        if business_intent == "pricing":
            return {
                "minimum_test_size": "20–50 potential customers",
                "healthy_conversion": "8–15%",
                "warning_conversion": "below 3%",
                "budget_guardrail": f"Do not risk more than ${max(300, int(budget * 0.1))} before seeing proof"
            }

        if business_intent == "growth":
            return {
                "minimum_test_size": "50–100 people reached",
                "healthy_conversion": "5–12%",
                "warning_conversion": "below 2%",
                "budget_guardrail": f"Do not spend more than ${max(300, int(budget * 0.15))} on unproven channels"
            }

        return {
            "minimum_test_size": "20–50 real prospects",
            "healthy_conversion": "5–10%",
            "warning_conversion": "below 2%",
            "budget_guardrail": f"Protect at least ${int(budget * 0.7)} until demand is proven"
        }


decision_depth_engine = DecisionDepthEngine()