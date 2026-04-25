class BusinessStrategyEngine:

    def generate_strategy(self, intent: str, scenario: dict):

        if intent == "pricing":
            return {
                "advice": (
                    "Start with competitive pricing slightly below the market so early customers "
                    "have a reason to try you before your brand is trusted."
                ),
                "steps": [
                    "Research competitors in your area",
                    "Set your first price 5–10% lower than similar options",
                    "Track how many people buy after seeing the price"
                ]
            }

        if intent == "growth":
            return {
                "advice": (
                    "Focus on one growth channel first instead of trying everything at once. "
                    "This helps you find what works without wasting money."
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
                    "Protect your cash first. Cut non-essential spending and keep only what helps "
                    "you get or serve customers."
                ),
                "steps": [
                    "List all monthly expenses",
                    "Remove anything not tied to customers or operations",
                    "Track weekly cash flow"
                ]
            }

        if intent == "acquisition":
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
                    "Enter the market by focusing on one small niche first. Competing everywhere "
                    "too early makes it harder to stand out."
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


business_strategy_engine = BusinessStrategyEngine()