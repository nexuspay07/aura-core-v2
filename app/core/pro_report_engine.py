class ProReportEngine:

    def generate(self, goal: str, decision_brief: dict, comparison: dict):
        best = comparison.get("best_strategy", {})
        strategies = comparison.get("comparisons", [])

        report = {
            "title": "AURA Pro Decision Report",

            "summary": decision_brief.get("recommended_move"),

            "strategy_breakdown": [
                {
                    "strategy": s["strategy"],
                    "why_it_works": s["reason"],
                    "risk": s["risk"]
                }
                for s in strategies
            ],

            "scenarios": {
                "best_case": "Strong traction and rapid growth if execution is correct.",
                "expected_case": "Moderate growth with steady improvement.",
                "worst_case": "Low traction requiring pivot or adjustment."
            },

            "risk_analysis": {
                "main_risk": decision_brief.get("main_risk"),
                "mitigation": "Start small, validate early, adjust quickly."
            },

            "execution_plan": [
                "Define your offer clearly",
                "Test with a small audience",
                "Measure response",
                "Adjust pricing or positioning",
                "Scale what works"
            ],

            "30_day_plan": {
                "week_1": "Research and validate idea",
                "week_2": "Run first test",
                "week_3": "Analyze results",
                "week_4": "Scale or pivot"
            }
        }

        return report


pro_report_engine = ProReportEngine()