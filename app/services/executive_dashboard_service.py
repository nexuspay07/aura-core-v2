class ExecutiveDashboardService:

    """
    Converts Aura intelligence into a clean
    Executive Dashboard response.
    """

    def build(self, intelligence: dict):

        executive = intelligence.get(
            "executive_response",
            {}
        )

        advisor = intelligence.get(
            "executive_advisor",
            {}
        )

        synthesis = intelligence.get(
            "executive_synthesis",
            {}
        )

        operational = intelligence.get(
            "operational_intelligence",
            {}
        )

        prediction = intelligence.get(
            "prediction",
            {}
        )

        return {

            "headline": executive.get(
                "headline",
                "Aura analyzed your business."
            ),

            "summary": executive.get(
                "summary",
                "No executive summary available."
            ),

            "business_health": operational.get(
                "overall_health",
                "Unknown"
            ),

            "top_priority": advisor.get(
                "top_priority",
                "No priority identified."
            ),

            "recommended_action": advisor.get(
                "recommended_action",
                "Continue monitoring."
            ),

            "confidence": prediction.get(
                "confidence",
                None
            ),

            "reasoning": synthesis.get(
                "reasoning",
                []
            ),

            "warnings": synthesis.get(
                "warnings",
                []
            ),

            "next_steps": advisor.get(
                "next_steps",
                []
            )

        }


executive_dashboard_service = ExecutiveDashboardService()