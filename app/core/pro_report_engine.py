class ProReportEngine:

    def generate(self, goal: str, decision_brief: dict, comparison: dict):
        strategies = comparison.get("comparisons", [])

        recommended_move = decision_brief.get(
            "recommended_move",
            "No recommendation available."
        )

        market_pressure = decision_brief.get(
            "market_pressure",
            "Market pressure could not be fully analyzed."
        )

        main_risk = decision_brief.get(
            "main_risk",
            "The main risk is weak validation before execution."
        )

        fallback = decision_brief.get(
            "fallback_move",
            "Start small, validate early, and adjust quickly."
        )

        report = {
            "title": "AURA Pro Decision Report",

            # -----------------------------
            # EXECUTIVE SUMMARY
            # -----------------------------
            "summary": recommended_move,

            "executive_summary": {
                "decision": recommended_move,
                "why_now": (
                    "This decision matters because early execution choices affect cost, speed, "
                    "customer trust, and survival. AURA recommends starting with a focused, "
                    "low-waste path before committing more money."
                ),
                "strategic_position": (
                    "Your safest advantage is not trying to look bigger than competitors. "
                    "Your advantage is focus, speed, customer learning, and sharper positioning."
                )
            },

            # -----------------------------
            # MARKET INTELLIGENCE
            # -----------------------------
            "market_reality": decision_brief.get("market_context"),
            "market_pressure": market_pressure,
            "survival_strategy": decision_brief.get("survival_strategy"),
            "growth_angle": decision_brief.get("growth_angle"),
            "premium_insight": decision_brief.get("premium_insight"),

            # -----------------------------
            # REALITY ENGINE
            # -----------------------------
            "reality_engine": {
                "reality_check": decision_brief.get("reality_check"),
                "brutal_truth": decision_brief.get("brutal_truth"),
                "why_not_aggressive": decision_brief.get("why_not_aggressive"),
                "why_not_balanced": decision_brief.get("why_not_balanced"),
                "why_this_strategy_wins": decision_brief.get("why_this_strategy_wins"),
            },

            # -----------------------------
            # DECISION DEPTH
            # -----------------------------
            "decision_depth": {
                "personalized_reality": decision_brief.get("personalized_reality"),
                "consequence_simulation": decision_brief.get("consequence_simulation"),
                "competitor_threat": decision_brief.get("competitor_threat"),
                "hidden_opportunity": decision_brief.get("hidden_opportunity"),
                "failure_triggers": decision_brief.get("failure_triggers"),
                "numbers_to_watch": decision_brief.get("numbers_to_watch"),
            },

            # -----------------------------
            # STRATEGY OPTIONS
            # -----------------------------
            "strategy_breakdown": [
                {
                    "strategy": s.get("strategy"),
                    "why_it_works": s.get("reason"),
                    "risk": s.get("risk"),
                    "score": s.get("score")
                }
                for s in strategies
            ],

            "strategy_decision": {
                "recommended_strategy": recommended_move,
                "why_this_over_others": (
                    "AURA selected this path because it protects capital, reduces avoidable risk, "
                    "and allows fast learning before scaling."
                ),
                "wrong_strategy_warning": (
                    "The wrong strategy here would be spending too early before proving demand. "
                    "That can create the illusion of activity without real customer traction."
                )
            },

            # -----------------------------
            # ONLINE VS OFFLINE / EXECUTION LOGIC
            # -----------------------------
            "business_path_analysis": {
                "online_first": {
                    "cost": "Lower startup cost",
                    "risk": "Lower financial risk",
                    "speed": "Faster testing and faster feedback",
                    "best_for": "Testing demand, building trust, and validating the offer before expansion"
                },
                "offline_first": {
                    "cost": "Higher startup cost",
                    "risk": "Higher financial risk",
                    "speed": "Slower validation because rent, inventory, or setup costs may come first",
                    "best_for": "Businesses that already have proven demand or local customer commitment"
                },
                "recommended_path": (
                    "Start online or digitally-assisted first, validate demand, build proof, then consider offline expansion."
                )
            },

            # -----------------------------
            # SCENARIOS
            # -----------------------------
            "scenarios": {
                "best_case": (
                    "Strong traction if your niche is clear, your offer solves a painful problem, "
                    "and you build trust early through proof, testimonials, or direct customer conversations."
                ),
                "expected_case": (
                    "Moderate growth through small tests, customer feedback, positioning improvement, "
                    "and focused execution."
                ),
                "worst_case": (
                    "Low traction if positioning is weak, trust is low, pricing is unclear, "
                    "or the offer is too broad."
                )
            },

            # -----------------------------
            # NUMBERS / METRICS
            # -----------------------------
            "numbers_to_watch": {
                "minimum_test_size": "20–50 real prospects before making a bigger decision",
                "healthy_signal": "5–15% of people show strong interest or take action",
                "danger_signal": "Below 3% response or conversion means the offer needs work",
                "trust_signal": "People ask serious buying questions, request details, or refer others",
                "pivot_signal": "People understand the offer but still do not care enough to act"
            },

            "financial_guardrails": {
                "max_test_spend": "Do not spend more than 10–15% of your budget before validation",
                "safe_budget_usage": "Protect at least 70% of capital until demand is proven",
                "spending_rule": (
                    "Spend only on things that directly create learning, trust, or customer acquisition. "
                    "Avoid branding, large inventory, rent, or unnecessary tools too early."
                )
            },

            # -----------------------------
            # FAILURE PREDICTION
            # -----------------------------
            "failure_prediction": [
                "If conversion is below 3%, the offer is not strong enough yet",
                "If customers hesitate, trust, clarity, or proof is missing",
                "If people show interest but do not buy, pricing or value mismatch exists",
                "If you are spending before learning, you may burn money without traction",
                "If your offer targets everyone, it may feel specific to no one"
            ],

            "failure_recovery": {
                "if_no_interest": "Narrow the customer group and make the problem more specific",
                "if_interest_no_sales": "Improve proof, offer clarity, pricing, or urgency",
                "if_sales_but_low_profit": "Adjust pricing, reduce delivery cost, or bundle value",
                "if_competitors_win": "Differentiate by speed, niche focus, trust, or customer experience"
            },

            # -----------------------------
            # RISK ANALYSIS
            # -----------------------------
            "risk_analysis": {
                "main_risk": main_risk,
                "mitigation": fallback,
                "risk_level": decision_brief.get("risk_profile", "medium"),
                "risk_note": (
                    "The goal is not to remove all risk. The goal is to take small, controlled risks "
                    "that produce useful learning before bigger spending."
                )
            },

            # -----------------------------
            # EXECUTION PLAN
            # -----------------------------
            "execution_plan": [
                "Day 1–2: Define one narrow customer segment and one painful problem",
                "Day 3–5: Create a simple offer with a clear promise and basic pricing",
                "Day 6–10: Talk to 20–50 real prospects or run a small test",
                "Day 11–15: Track objections, confusion, interest, and buying signals",
                "Day 16–20: Improve positioning, proof, pricing, or offer structure",
                "Day 21–25: Repeat the test with the improved message",
                "Day 26–30: Scale only if response improves; otherwise pivot the niche or offer"
            ],

            "30_day_plan": {
                "week_1": "Define niche, problem, offer, and simple customer message",
                "week_2": "Test with real prospects and collect objections",
                "week_3": "Improve pricing, message, proof, and trust signals",
                "week_4": "Scale the strongest channel or pivot if traction is weak"
            },

            # -----------------------------
            # FINAL VERDICT
            # -----------------------------
            "final_verdict": {
                "what_to_do_now": recommended_move,
                "what_not_to_do": (
                    "Do not spend heavily, rent space, hire too early, or build a big operation "
                    "before proving customer demand."
                ),
                "success_condition": (
                    "Success means getting real customer signals before increasing spending."
                ),
                "next_check_in": (
                    "After testing, return to AURA with results like: conversion was low, people liked it but did not buy, "
                    "or customers asked for a cheaper option."
                )
            }
        }

        return report


pro_report_engine = ProReportEngine()