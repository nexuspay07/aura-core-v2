class ExecutiveSynthesisEngine:
    """
    Phase 65

    Converts all intelligence outputs into
    one coherent executive recommendation.

    Hybrid Personality:
    - Executive Advisor
    - Strategic Co-Founder
    """

    def synthesize(
        self,
        goal: str,
        strategic_analysis: dict,
        market_intelligence: dict,
        competitive_intelligence: dict,
        business_understanding: dict,
        dynamic_reasoning: dict,
        prediction: dict,
        strategic_simulation: dict,
        operational_intelligence: dict,
        strategy_reinforcement: dict,
        deep_reasoning: dict | None = None
    ):

        deep_reasoning = deep_reasoning or {}

        business_dna = business_understanding.get(
            "business_dna",
            {}
        )

        stage = business_dna.get(
            "business_stage",
            "unknown"
        )

        opportunity = market_intelligence.get(
            "opportunity_score",
            50
        )

        threat = market_intelligence.get(
            "threat_score",
            50
        )

        confidence = int(
            prediction.get(
                "confidence",
                0.65
            ) * 100
        )

        risk_level = dynamic_reasoning.get(
            "risk_level",
            "medium"
        )

        recommended_strategy = strategic_analysis.get(
            "recommended_strategy",
            "Balanced"
        )

        strategic_warning = dynamic_reasoning.get(
            "strategic_warning",
            ""
        )

        operational_warning = operational_intelligence.get(
            "operational_warning",
            ""
        )

        scale_readiness = operational_intelligence.get(
            "scale_readiness",
            ""
        )

        recommendation = self._generate_recommendation(
            goal,
            stage,
            recommended_strategy,
            opportunity,
            threat,
            risk_level,
            confidence
        )

        reasoning = [
            f"Market opportunity score is {opportunity}.",
            f"Threat score is {threat}.",
            f"Current business stage appears to be '{stage}'.",
            f"Recommended strategy is '{recommended_strategy}'.",
            strategic_warning,
            operational_warning,
            scale_readiness
        ]

        reasoning.extend(
            deep_reasoning.get(
                "reasoning_chain",
                []
            )
        )

        alternatives = self._alternatives(
            recommended_strategy
        )

        alternatives.extend(
            deep_reasoning.get(
                "alternative_options",
                []
            )
        )

        risks = []

        if strategic_warning:
            risks.append(strategic_warning)

        if operational_warning:
            risks.append(operational_warning)

        root_problem = deep_reasoning.get(
            "root_problem"
        )

        if root_problem:
            risks.append(root_problem)

        next_actions = (
            operational_intelligence.get(
                "operations_next_steps",
                []
            )
        )

        verdict = self._verdict(
            opportunity,
            threat,
            confidence,
            risk_level
        )

        return {
            "executive_recommendation":
                recommendation,

            "verdict":
                verdict,

            "confidence":
                confidence,

            "reasoning":
                reasoning,

            "alternatives":
                alternatives,

            "risks":
                risks,

            "deep_reasoning":
                deep_reasoning,

            "root_problem":
                root_problem,

            "recommended_option":
                deep_reasoning.get(
                    "recommended_option"
                ),

            "next_actions":
                next_actions
        }

    def _generate_recommendation(
        self,
        goal,
        stage,
        strategy,
        opportunity,
        threat,
        risk,
        confidence
    ):

        if opportunity > threat:

            if stage == "early_stage":

                return (
                    f"For '{goal}', I recommend "
                    f"moving cautiously. The opportunity "
                    f"appears attractive, but the business "
                    f"should strengthen execution systems "
                    f"before aggressive expansion."
                )

            return (
                f"For '{goal}', the current signals "
                f"support pursuing the opportunity "
                f"using a {strategy.lower()} approach."
            )

        return (
            f"For '{goal}', I do not recommend "
            f"aggressive action at this time. "
            f"The risk environment currently "
            f"outweighs the upside."
        )

    def _alternatives(
        self,
        strategy
    ):

        if strategy == "Aggressive":

            return [
                "Balanced execution strategy",
                "Strategic partnerships",
                "Pilot testing before scaling"
            ]

        if strategy == "Conservative":

            return [
                "Balanced execution strategy",
                "Limited experimentation",
                "Selective expansion"
            ]

        return [
            "Aggressive expansion",
            "Conservative positioning",
            "Strategic partnerships"
        ]

    def _verdict(
        self,
        opportunity,
        threat,
        confidence,
        risk
    ):

        if (
            opportunity > threat
            and confidence >= 70
            and risk != "high"
        ):

            return (
                "Proceed with confidence."
            )

        if opportunity > threat:

            return (
                "Proceed cautiously."
            )

        return (
            "Delay major commitments."
        )


executive_synthesis_engine = (
    ExecutiveSynthesisEngine()
)
