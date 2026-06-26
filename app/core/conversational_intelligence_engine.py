class ConversationalIntelligenceEngine:
    """
    Phase 68

    Conversational Intelligence Engine

    Converts Aura's executive intelligence into
    natural executive-quality conversations.
    """

    def generate(
        self,
        goal: str,
        executive_advisor: dict,
        standardized_output: dict,
        executive_synthesis: dict
    ):

        summary = standardized_output.get(
            "executive_summary",
            ""
        )

        recommendation = executive_advisor.get(
            "advisor_recommendation",
            ""
        )

        truth = executive_advisor.get(
            "business_truth",
            ""
        )

        expected = executive_advisor.get(
            "expected_result",
            ""
        )

        warning = executive_advisor.get(
            "founder_warning",
            ""
        )

        confidence = executive_advisor.get(
            "confidence",
            executive_synthesis.get(
                "confidence",
                50
            )
        )

        decision = executive_advisor.get(
            "executive_decision",
            "Proceed cautiously."
        )

        return {

            "title": self._title(goal),

            "executive_brief": self._brief(summary),

            "analysis": self._analysis(
                truth,
                summary
            ),

            "recommendation": self._recommendation(
                recommendation
            ),

            "expected_outcome": expected,

            "warning": warning,

            "decision": decision,

            "confidence": confidence,

            "closing_message": self._closing(
                confidence
            )
        }

    def _title(
        self,
        goal
    ):

        return f"Executive Advisory Report"

    def _brief(
        self,
        summary
    ):

        return (
            "After evaluating your situation, "
            + summary
        )

    def _analysis(
        self,
        truth,
        summary
    ):

        return (
            f"{truth}\n\n"
            f"{summary}"
        )

    def _recommendation(
        self,
        recommendation
    ):

        return (
            "My recommendation is to "
            + recommendation
        )

    def _closing(
        self,
        confidence
    ):

        if confidence >= 85:

            return (
                "I have high confidence in this recommendation."
            )

        if confidence >= 70:

            return (
                "This recommendation is well supported by the available intelligence."
            )

        if confidence >= 50:

            return (
                "This recommendation should be validated with additional real-world evidence."
            )

        return (
            "More information is needed before making a major decision."
        )


conversational_intelligence_engine = (
    ConversationalIntelligenceEngine()
)