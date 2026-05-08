class DynamicReasoningEngine:

    def analyze(self, business_dna: dict):

        stage = business_dna.get("business_stage", "unknown_stage")
        model = business_dna.get("business_model", "general_business")
        competition = business_dna.get("competition_pressure", "medium")
        trust = business_dna.get("trust_dependency", "medium")
        scalability = business_dna.get("scalability", "medium")
        capital = business_dna.get("capital_intensity", "medium")
        proof = business_dna.get("proof_requirement", "medium")

        bottleneck = self._detect_bottleneck(
            stage,
            model,
            competition,
            trust,
            scalability,
            capital,
            proof
        )

        current_priority = self._detect_priority(
            stage,
            bottleneck
        )

        execution_focus = self._execution_focus(
            stage,
            model
        )

        growth_blocker = self._growth_blocker(
            stage,
            trust,
            competition
        )

        next_evolution = self._next_evolution(
            stage
        )

        strategic_warning = self._strategic_warning(
            stage,
            capital,
            competition
        )

        return {
            "current_bottleneck": bottleneck,
            "current_priority": current_priority,
            "execution_focus": execution_focus,
            "growth_blocker": growth_blocker,
            "next_business_evolution": next_evolution,
            "strategic_warning": strategic_warning,
        }

    def _detect_bottleneck(
        self,
        stage,
        model,
        competition,
        trust,
        scalability,
        capital,
        proof
    ):

        if stage == "early_stage":

            if trust in ["high", "very_high"]:
                return (
                    "Customers may hesitate because trust and proof are still weak."
                )

            if competition in ["high", "very_high"]:
                return (
                    "The business may struggle to stand out clearly from competitors."
                )

            return (
                "The biggest bottleneck is validating real customer demand."
            )

        if stage == "growth_stage":

            if scalability in ["low", "medium"]:
                return (
                    "Operations may become overloaded as customer volume increases."
                )

            return (
                "The business may struggle to scale systems fast enough."
            )

        if stage == "survival_stage":

            if capital in ["high", "very_high"]:
                return (
                    "High operating pressure may create financial instability."
                )

            return (
                "The business may be losing efficiency or market relevance."
            )

        return (
            "The business still needs clearer market validation and positioning."
        )

    def _detect_priority(self, stage, bottleneck):

        if stage == "early_stage":
            return (
                "Validate demand quickly before scaling spending."
            )

        if stage == "growth_stage":
            return (
                "Build repeatable systems before increasing acquisition."
            )

        if stage == "survival_stage":
            return (
                "Reduce pressure, simplify operations, and stabilize cash flow."
            )

        return (
            "Clarify positioning and improve customer understanding."
        )

    def _execution_focus(self, stage, model):

        if stage == "early_stage":

            if model == "digital_product_or_platform":
                return (
                    "Focus on fast testing, onboarding feedback, and proof of results."
                )

            if model == "service_business":
                return (
                    "Focus on direct outreach, testimonials, and relationship building."
                )

            return (
                "Focus on learning quickly and validating customer behavior."
            )

        if stage == "growth_stage":
            return (
                "Focus on systems, team structure, customer retention, and operational consistency."
            )

        if stage == "survival_stage":
            return (
                "Focus on efficiency, reducing waste, and improving profitability."
            )

        return (
            "Focus on clearer positioning and disciplined execution."
        )

    def _growth_blocker(self, stage, trust, competition):

        if stage == "early_stage":

            if trust in ["high", "very_high"]:
                return (
                    "Lack of proof and credibility may slow customer conversion."
                )

            if competition in ["high", "very_high"]:
                return (
                    "Weak differentiation may make customer acquisition difficult."
                )

            return (
                "Unclear customer demand may slow growth."
            )

        if stage == "growth_stage":
            return (
                "Operational bottlenecks may slow scaling."
            )

        if stage == "survival_stage":
            return (
                "Financial pressure may limit growth flexibility."
            )

        return (
            "The business still needs stronger strategic clarity."
        )

    def _next_evolution(self, stage):

        if stage == "early_stage":
            return (
                "The next evolution is moving from idea validation to repeatable customer acquisition."
            )

        if stage == "growth_stage":
            return (
                "The next evolution is transforming from founder-driven execution into scalable systems."
            )

        if stage == "survival_stage":
            return (
                "The next evolution is restructuring operations for long-term stability."
            )

        return (
            "The next evolution is achieving clearer market positioning."
        )

    def _strategic_warning(self, stage, capital, competition):

        if stage == "early_stage":

            if competition in ["high", "very_high"]:
                return (
                    "Trying to compete broadly too early may waste time and money."
                )

            return (
                "Scaling before validation may increase risk."
            )

        if stage == "growth_stage":
            return (
                "Growing faster than operational capacity may damage customer experience."
            )

        if stage == "survival_stage":

            if capital in ["high", "very_high"]:
                return (
                    "Financial pressure may become dangerous if costs are not controlled quickly."
                )

            return (
                "Operational inefficiency may continue reducing profitability."
            )

        return (
            "Weak positioning may reduce long-term competitiveness."
        )


dynamic_reasoning_engine = DynamicReasoningEngine()