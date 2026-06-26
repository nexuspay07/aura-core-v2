class ChatResponseEngine:
    """
    Phase 70

    Final response generator.

    This is the final layer before information
    reaches the frontend.

    It converts Aura's executive intelligence
    into a polished executive conversation.
    """

    def generate(
        self,
        goal: str,
        conversational_response: dict,
        executive_advisor: dict,
        standardized_output: dict
    ):

        title = conversational_response.get(
            "title",
            "Executive Advisory Report"
        )

        brief = conversational_response.get(
            "executive_brief",
            ""
        )

        analysis = conversational_response.get(
            "analysis",
            ""
        )

        recommendation = conversational_response.get(
            "recommendation",
            ""
        )

        expected = conversational_response.get(
            "expected_outcome",
            ""
        )

        warning = conversational_response.get(
            "warning",
            ""
        )

        decision = conversational_response.get(
            "decision",
            ""
        )

        confidence = conversational_response.get(
            "confidence",
            50
        )

        verdict = standardized_output.get(
            "executive_verdict",
            ""
        )

        final_message = self._build_message(
            goal,
            title,
            brief,
            analysis,
            recommendation,
            expected,
            warning,
            decision,
            confidence,
            verdict
        )

        return {

            "title": title,

            "goal": goal,

            "message": final_message,

            "confidence": confidence,

            "decision": decision,

            "warning": warning
        }

    def _build_message(
        self,
        goal,
        title,
        brief,
        analysis,
        recommendation,
        expected,
        warning,
        decision,
        confidence,
        verdict
    ):

        return f"""
{title}

Question

{goal}

Executive Summary

{brief}

Business Analysis

{analysis}

Recommendation

{recommendation}

Expected Business Outcome

{expected}

Decision

{decision}

Confidence

{confidence}%

Founder Warning

{warning}

Executive Verdict

{verdict}
""".strip()


chat_response_engine = ChatResponseEngine()