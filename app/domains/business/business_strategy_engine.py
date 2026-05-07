class BusinessStrategyEngine:

    def generate_strategy(self, intent: str, scenario: dict):
        goal = scenario.get("goal", "").lower()
        budget = scenario.get("budget", 10000)

        if self._is_online_vs_offline(goal):
            if budget <= 5000:
                return {
                    "advice": (
                        "Start online first, then move offline only after demand is proven. "
                        "With a small budget, online gives you cheaper testing, faster feedback, "
                        "and lower risk than renting space or building a physical setup too early."
                    ),
                    "steps": [
                        "Create a simple online offer or page",
                        "Test demand with real customers",
                        "Move offline only after people show real buying interest"
                    ]
                }

            return {
                "advice": (
                    "Use a hybrid approach: validate online first, then use offline presence "
                    "to increase trust, visibility, and customer experience."
                ),
                "steps": [
                    "Launch online to test demand",
                    "Build proof through reviews or early customers",
                    "Use offline expansion only when demand is validated"
                ]
            }

        if self._is_restaurant_or_food(goal):
            return {
                "advice": (
                    "For a restaurant or food business, start with one signature offer before expanding. "
                    "Use online presence for visibility, ordering, reviews, and trust, but avoid expensive offline setup "
                    "until repeat demand is proven."
                ),
                "steps": [
                    "Pick one signature food offer",
                    "Test it with a small local audience",
                    "Collect reviews, photos, and repeat orders before expanding"
                ]
            }

        if self._is_building_materials(goal):
            return {
                "advice": (
                    "For building materials, trust, availability, delivery speed, and supplier reliability matter more "
                    "than flashy marketing. Start by serving one clear customer type such as contractors, small builders, "
                    "or homeowners doing repairs."
                ),
                "steps": [
                    "Choose one customer type: contractors, builders, or homeowners",
                    "Offer reliable pricing, availability, and delivery",
                    "Build trust through consistency before expanding inventory"
                ]
            }

        if intent == "pricing":
            return {
                "advice": (
                    "Do not just undercut competitors. Use tiered pricing: a basic option for price-sensitive customers "
                    "and a higher-value option for customers who want quality, speed, or trust."
                ),
                "steps": [
                    "Research competitor prices",
                    "Create basic, standard, and premium options",
                    "Track which option customers choose most"
                ]
            }

        if intent == "growth":
            return {
                "advice": (
                    "Focus on one growth channel first instead of trying everything at once. "
                    "Your goal is to find the channel that produces real customers, not just attention."
                ),
                "steps": [
                    "Choose one growth channel",
                    "Test it with a small budget",
                    "Scale only if it brings real customers"
                ]
            }

        if intent == "cost":
            return {
                "advice": (
                    "Protect cash first. Remove spending that does not directly help you get customers, "
                    "serve customers, or prove demand."
                ),
                "steps": [
                    "List all monthly expenses",
                    "Remove anything not tied to customers or operations",
                    "Track weekly cash flow"
                ]
            }

        if intent in ["acquisition", "customer_acquisition"]:
            return {
                "advice": (
                    "Start with a small group of ideal customers instead of marketing to everyone. "
                    "This makes your message clearer and cheaper to test."
                ),
                "steps": [
                    "Define your ideal customer",
                    "Reach out to 10–20 people directly",
                    "Use their feedback to improve your offer"
                ]
            }

        if intent == "hiring":
            return {
                "advice": (
                    "Do not hire too early. Hire only when the work is repeated, necessary, "
                    "and clearly slowing the business down."
                ),
                "steps": [
                    "Identify the repeated task slowing you down",
                    "Estimate whether the role can pay for itself",
                    "Start with part-time or contract help first"
                ]
            }

        if intent == "market_entry":
            return {
                "advice": (
                    "Enter through one small niche first. Competing everywhere too early makes it harder to stand out."
                ),
                "steps": [
                    "Pick one customer segment",
                    "Offer one clear solution",
                    "Use early feedback before expanding"
                ]
            }

        return {
            "advice": (
                "Start small, validate your idea with real people, and grow only after you see demand."
            ),
            "steps": [
                "Test your idea with a small group",
                "Measure real interest",
                "Improve before spending more"
            ]
        }

    def _is_online_vs_offline(self, goal: str):
        return (
            ("online" in goal and "offline" in goal)
            or "physical store" in goal
            or "open a store" in goal
            or "online business first" in goal
            or "offline business first" in goal
            or "open online" in goal
            or "open offline" in goal
        )

    def _is_restaurant_or_food(self, goal: str):
        return any(x in goal for x in [
            "restaurant", "food", "cafe", "bakery", "pizza", "shawarma", "chicken"
        ])

    def _is_building_materials(self, goal: str):
        return any(x in goal for x in [
            "building material", "building materials", "construction materials",
            "cement", "tiles", "lumber", "hardware", "plumbing supplies"
        ])


business_strategy_engine = BusinessStrategyEngine()