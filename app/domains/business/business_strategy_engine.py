class BusinessStrategyEngine:

    def generate_strategy(self, intent: str, scenario: dict):

        if intent == "pricing":
            return {
                "advice": "Start with competitive pricing slightly below market to attract early customers.",
                "steps": [
                    "Research competitors in your area",
                    "Set initial price 5–10% lower",
                    "Adjust based on demand"
                ]
            }

        if intent == "growth":
            return {
                "advice": "Focus on one channel and scale gradually based on results.",
                "steps": [
                    "Choose one growth channel (ads, referrals, etc.)",
                    "Test with small budget",
                    "Scale what works"
                ]
            }

        if intent == "cost":
            return {
                "advice": "Reduce unnecessary expenses and focus only on essential operations.",
                "steps": [
                    "List all expenses",
                    "Cut non-essential costs",
                    "Optimize operations"
                ]
            }

        if intent == "acquisition":
            return {
                "advice": "Start by targeting a small group of ideal customers.",
                "steps": [
                    "Define your target customer",
                    "Reach out directly",
                    "Collect feedback and improve"
                ]
            }

        return {
            "advice": "Start small, validate your idea, and grow based on real demand.",
            "steps": [
                "Test your idea",
                "Get first customers",
                "Improve and scale"
            ]
        }


business_strategy_engine = BusinessStrategyEngine()