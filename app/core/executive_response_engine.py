class ExecutiveResponseEngine:

    def generate(
        self,
        goal,
        strategic_analysis,
        market_intelligence,
        competitive_intelligence,
        business_understanding,
        dynamic_reasoning,
        prediction,
        operational_intelligence,
        best_strategy
    ):

        confidence = int(
            prediction.get("confidence", 0.6) * 100
        )

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
            )
        ]

        recommendations = [
            dynamic_reasoning.get(
                "current_priority",
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
            "best_strategy": best_strategy,
            "confidence": confidence
        }


executive_response_engine = ExecutiveResponseEngine()