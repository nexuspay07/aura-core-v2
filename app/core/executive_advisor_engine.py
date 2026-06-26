class ExecutiveAdvisorEngine:
    """
    Phase 67

    Executive Advisor Engine

    Converts Aura's intelligence into practical
    executive-level business advice.
    """

    def advise(
        self,
        goal: str,
        executive_synthesis: dict,
        business_understanding: dict,
        dynamic_reasoning: dict,
        market_intelligence: dict,
        strategic_simulation: dict,
        operational_intelligence: dict
    ):

        opportunity = market_intelligence.get(
            "opportunity_score",
            50
        )

        threat = market_intelligence.get(
            "threat_score",
            50
        )

        confidence = executive_synthesis.get(
            "confidence",
            50
        )

        business_stage = (
            business_understanding
            .get("business_dna", {})
            .get("business_stage", "unknown")
        )

        core_problem = dynamic_reasoning.get(
            "growth_blocker",
            "No major blocker detected."
        )

        business_truth = self._business_truth(
            business_stage,
            opportunity,
            threat
        )

        recommendation = operational_intelligence.get(
            "recommended_operational_move",
            "Improve execution."
        )

        expected_result = self._expected_result(
            opportunity,
            business_stage
        )

        founder_warning = dynamic_reasoning.get(
            "strategic_warning",
            "Proceed carefully."
        )

        executive_decision = self._decision(
            opportunity,
            threat,
            confidence
        )

        return {

            "goal": goal,

            "core_problem": core_problem,

            "business_truth": business_truth,

            "advisor_recommendation": recommendation,

            "expected_result": expected_result,

            "founder_warning": founder_warning,

            "executive_decision": executive_decision,

            "confidence": confidence
        }

    def _business_truth(
        self,
        stage,
        opportunity,
        threat
    ):

        if stage == "early_stage":
            return (
                "The biggest challenge is proving repeatable customer demand "
                "before attempting rapid expansion."
            )

        if stage == "growth_stage":
            return (
                "Growth is possible, but stronger systems are needed to "
                "avoid operational bottlenecks."
            )

        if opportunity > threat:
            return (
                "The market opportunity currently outweighs the risks."
            )

        return (
            "Execution quality will determine success more than market conditions."
        )

    def _expected_result(
        self,
        opportunity,
        stage
    ):

        if stage == "early_stage":
            return (
                "Higher customer validation, stronger trust, and a more "
                "repeatable business model."
            )

        if opportunity >= 80:
            return (
                "Strong revenue growth potential if execution remains disciplined."
            )

        if opportunity >= 60:
            return (
                "Moderate business improvement with controlled execution."
            )

        return (
            "Limited improvement unless the strategy changes."
        )

    def _decision(
        self,
        opportunity,
        threat,
        confidence
    ):

        if opportunity >= 80 and confidence >= 75:
            return "Proceed confidently."

        if opportunity >= 60:
            return "Proceed cautiously."

        if threat > opportunity:
            return "Delay expansion and strengthen the business first."

        return "Collect more evidence before making a major decision."


executive_advisor_engine = ExecutiveAdvisorEngine()