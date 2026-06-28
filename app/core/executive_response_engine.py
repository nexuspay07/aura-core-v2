class ExecutiveResponseEngine:

    def generate(
    self,
    goal,
    strategic_analysis,
    market_intelligence,
    competitive_intelligence,
    business_understanding,
    dynamic_reasoning,
    deep_reasoning,
    prediction,
    operational_intelligence,
    best_strategy
):

        confidence = int(
            prediction.get("confidence", 0.6) * 100
        )

        deep_reasoning = deep_reasoning or {}

        summary = (
            f"For '{goal}', I recommend moving cautiously. "
            f"The opportunity appears attractive, but execution "
            f"systems should be strengthened before aggressive expansion."
        )

        findings = [
            f"Market opportunity score is {market_intelligence.get('opportunity_score', 'unknown')}.",
            f"Competition level is {market_intelligence.get('competition_level', 'unknown')}.",
            dynamic_reasoning.get(
                "current_bottleneck",
                "Execution remains the primary challenge."
            ),
            deep_reasoning.get(
                "root_problem",
                "No deeper root problem detected."
            )
        ]

        recommendations = [
            dynamic_reasoning.get(
                "current_priority",
                ""
            ),
            deep_reasoning.get(
                "recommended_option",
                ""
            ),
            operational_intelligence.get(
                "recommended_operational_move",
                ""
            )
        ]

        risks = [
            dynamic_reasoning.get(
                "strategic_warning",
                ""
            )
        ]

        if deep_reasoning.get("business_impact"):
            findings.append(
                deep_reasoning["business_impact"]
            )

        next_steps = (
            operational_intelligence.get(
                "operations_next_steps",
                []
            )
        )

        return {
            "executive_summary": summary,
            "key_findings": findings,
            "recommendations": recommendations,
            "risks": risks,
            "next_steps": next_steps,
            "deep_reasoning": deep_reasoning,
            "best_strategy": best_strategy,
            "confidence": confidence
        }


executive_response_engine = ExecutiveResponseEngine()
