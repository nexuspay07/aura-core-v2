class OutputStandardizationEngine:
    """
    Phase 66.6

    Converts raw Aura intelligence into
    executive-grade structured output.
    """

    def standardize(
        self,
        executive_response,
        strategic_simulation,
        operational_intelligence,
        dynamic_reasoning
    ):

        summary = executive_response.get(
            "executive_summary",
            "No summary available."
        )

        findings = executive_response.get(
            "key_findings",
            []
        )

        recommendations = executive_response.get(
            "recommendations",
            []
        )

        risks = executive_response.get(
            "risks",
            []
        )

        next_steps = executive_response.get(
            "next_steps",
            []
        )

        projection_30 = strategic_simulation.get(
            "30_day_projection",
            ""
        )

        projection_90 = strategic_simulation.get(
            "90_day_projection",
            ""
        )

        operational_move = operational_intelligence.get(
            "recommended_operational_move",
            ""
        )

        final_warning = dynamic_reasoning.get(
            "strategic_warning",
            ""
        )

        return {
            "executive_summary": summary,

            "key_insights": findings,

            "strategic_recommendation": recommendations,

            "primary_risks": risks,

            "next_30_days": projection_30,

            "next_90_days": projection_90,

            "operational_priority": operational_move,

            "final_warning": final_warning,

            "executive_verdict": self._build_verdict(
                summary,
                recommendations,
                risks
            )
        }

    def _build_verdict(
        self,
        summary,
        recommendations,
        risks
    ):

        recommendation = (
            recommendations[0]
            if recommendations
            else "Proceed carefully."
        )

        risk = (
            risks[0]
            if risks
            else "No major risks detected."
        )

        return (
            f"{summary}\n\n"
            f"Recommended Action: {recommendation}\n\n"
            f"Primary Risk: {risk}"
        )


output_standardization_engine = OutputStandardizationEngine()