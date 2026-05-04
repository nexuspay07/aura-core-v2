class ProReportEngine:

    def generate(self, goal: str, decision_brief: dict, comparison: dict):
        strategies = comparison.get("comparisons", [])

        report = {
            "title": "AURA Pro Decision Report",

            "summary": decision_brief.get(
                "recommended_move",
                "No recommendation available."
            ),

            "market_reality": decision_brief.get("market_context"),
            "market_pressure": decision_brief.get("market_pressure"),
            "survival_strategy": decision_brief.get("survival_strategy"),
            "growth_angle": decision_brief.get("growth_angle"),
            "premium_insight": decision_brief.get("premium_insight"),

            "reality_engine": {
                "reality_check": decision_brief.get("reality_check"),
                "brutal_truth": decision_brief.get("brutal_truth"),
                "why_not_aggressive": decision_brief.get("why_not_aggressive"),
                "why_not_balanced": decision_brief.get("why_not_balanced"),
                "why_this_strategy_wins": decision_brief.get("why_this_strategy_wins"),
            },

            "decision_depth": {
                "personalized_reality": decision_brief.get("personalized_reality"),
                "consequence_simulation": decision_brief.get("consequence_simulation"),
                "competitor_threat": decision_brief.get("competitor_threat"),
                "hidden_opportunity": decision_brief.get("hidden_opportunity"),
                "failure_triggers": decision_brief.get("failure_triggers"),
                "numbers_to_watch": decision_brief.get("numbers_to_watch"),
            },

            "strategy_breakdown": [
                {
                    "strategy": s.get("strategy"),
                    "why_it_works": s.get("reason"),
                    "risk": s.get("risk"),
                    "score": s.get("score")
                }
                for s in strategies
            ],

            "scenarios": {
                "best_case": "Strong traction if the niche is clear, the offer solves a painful problem, and trust is built early.",
                "expected_case": "Moderate growth through small tests, direct customer feedback, and focused execution.",
                "worst_case": "Low traction if positioning is weak, trust is low, pricing is unclear, or the offer is too broad."
            },

            "risk_analysis": {
                "main_risk": decision_brief.get("main_risk"),
                "mitigation": decision_brief.get(
                    "fallback_move",
                    "Start small, validate early, and adjust quickly."
                )
            },

            "execution_plan": [
                "Day 1–2: Define a narrow customer segment with a clear problem",
                "Day 3–5: Create a simple offer and message",
                "Day 6–10: Test with 20–50 real prospects",
                "Day 11–15: Identify objections and refine positioning",
                "Day 16–30: Scale only the message that converts"
            ],

            "30_day_plan": {
                "week_1": "Define niche and test demand through conversations",
                "week_2": "Run small tests and collect real feedback",
                "week_3": "Improve pricing, message, and trust signals",
                "week_4": "Scale or pivot based on conversion data"
            },

            "failure_prediction": [
                "If conversion is below 3%, the offer is not strong enough",
                "If customers hesitate, trust or clarity is missing",
                "If interest is high but no sales, pricing or value mismatch exists"
            ],

            "financial_guardrails": {
                "max_test_spend": "Do not spend more than 10–15% of your budget before validation",
                "safe_budget_usage": "Protect at least 70% of capital until demand is proven"
            }
        }

        return report


pro_report_engine = ProReportEngine()