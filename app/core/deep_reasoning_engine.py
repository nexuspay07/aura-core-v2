class DeepReasoningEngine:
    """
    Phase 71

    Deep Reasoning Engine

    Performs multi-step executive reasoning before
    Aura generates its final response.
    """

    def analyze(
        self,
        goal: str,
        business_understanding: dict,
        dynamic_reasoning: dict,
        market_intelligence: dict,
        competitive_intelligence: dict,
        prediction: dict,
        strategic_simulation: dict
    ):

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

        confidence = prediction.get(
            "confidence",
            0.70
        )

        blocker = dynamic_reasoning.get(
            "growth_blocker",
            "No major blocker detected."
        )

        observations = self._observations(
            stage,
            opportunity,
            threat,
            blocker
        )

        reasoning_chain = self._reasoning(
            observations,
            confidence
        )

        alternatives = self._alternatives(
            stage,
            opportunity
        )

        recommendation = self._recommendation(
            opportunity,
            threat
        )

        impact = self._impact(
            recommendation,
            stage
        )

        return {

            "root_problem": blocker,

            "observations": observations,

            "reasoning_chain": reasoning_chain,

            "alternative_options": alternatives,

            "recommended_option": recommendation,

            "business_impact": impact,

            "confidence": round(
                confidence * 100,
                2
            )
        }

    def _observations(
        self,
        stage,
        opportunity,
        threat,
        blocker
    ):

        items = []

        items.append(
            f"Business stage: {stage}"
        )

        items.append(
            f"Market opportunity score: {opportunity}"
        )

        items.append(
            f"Threat score: {threat}"
        )

        items.append(
            f"Primary business blocker: {blocker}"
        )

        return items

    def _reasoning(
        self,
        observations,
        confidence
    ):

        chain = []

        for observation in observations:

            chain.append(
                f"Observation: {observation}"
            )

        if confidence >= 0.80:

            chain.append(
                "Confidence is high enough to recommend immediate execution."
            )

        elif confidence >= 0.60:

            chain.append(
                "Confidence is moderate. Validate assumptions before scaling."
            )

        else:

            chain.append(
                "Confidence is limited. Gather additional evidence first."
            )

        return chain

    def _alternatives(
        self,
        stage,
        opportunity
    ):

        options = []

        options.append(
            "Increase marketing investment."
        )

        options.append(
            "Improve operational efficiency."
        )

        options.append(
            "Increase customer retention."
        )

        if stage == "early_stage":

            options.append(
                "Validate product-market fit."
            )

        if opportunity >= 80:

            options.append(
                "Accelerate strategic expansion."
            )

        return options

    def _recommendation(
        self,
        opportunity,
        threat
    ):

        if opportunity > threat:

            return (
                "Improve customer retention before pursuing aggressive expansion."
            )

        return (
            "Reduce strategic risk before expanding operations."
        )

    def _impact(
        self,
        recommendation,
        stage
    ):

        if stage == "early_stage":

            return (
                "Higher customer validation and stronger market fit."
            )

        return (
            f"Expected impact: {recommendation}"
        )


deep_reasoning_engine = DeepReasoningEngine()