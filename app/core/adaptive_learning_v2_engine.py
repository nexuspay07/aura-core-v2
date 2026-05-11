class AdaptiveLearningV2Engine:
    """
    Adaptive Learning V2

    This engine reads decision memory patterns and converts them into
    learning insights AURA can use to adapt future recommendations.
    """

    def analyze(self, memory_summary: dict, current_pipeline: dict | None = None):
        current_pipeline = current_pipeline or {}

        if not memory_summary or not memory_summary.get("has_memory"):
            return {
                "learning_active": False,
                "pattern_detected": "No repeated decision pattern detected yet.",
                "repeated_risk": None,
                "strategic_drift": "Not enough history to detect drift.",
                "recommended_adjustment": "Ask more related questions so AURA can learn your decision pattern.",
                "learning_priority": "Build initial decision history.",
            }

        repeated_model = memory_summary.get("repeated_business_model")
        repeated_risk = memory_summary.get("repeated_risk")
        repeated_warning = memory_summary.get("repeated_warning")
        total = memory_summary.get("total_decisions", 0)

        business_dna = current_pipeline.get("business_dna", {})
        dynamic_reasoning = current_pipeline.get("dynamic_reasoning", {})
        operational = current_pipeline.get("operational_intelligence", {})
        simulation = current_pipeline.get("strategic_simulation", {})

        pattern_detected = self._pattern_detected(
            total,
            repeated_model,
            repeated_risk,
            repeated_warning
        )

        strategic_drift = self._strategic_drift(
            repeated_risk,
            repeated_warning,
            dynamic_reasoning,
            operational
        )

        recommended_adjustment = self._recommended_adjustment(
            repeated_risk,
            repeated_warning,
            business_dna,
            dynamic_reasoning,
            operational,
            simulation
        )

        learning_priority = self._learning_priority(
            repeated_risk,
            business_dna,
            operational
        )

        return {
            "learning_active": True,
            "total_memory_records": total,
            "pattern_detected": pattern_detected,
            "repeated_business_model": repeated_model,
            "repeated_risk": repeated_risk,
            "repeated_warning": repeated_warning,
            "strategic_drift": strategic_drift,
            "recommended_adjustment": recommended_adjustment,
            "learning_priority": learning_priority,
        }

    def _pattern_detected(self, total, model, risk, warning):
        if total <= 1:
            return "AURA has started building memory, but needs more decisions to detect strong patterns."

        parts = []

        if model:
            parts.append(
                f"You are repeatedly exploring {model.replace('_', ' ')} decisions."
            )

        if risk:
            parts.append(
                f"Your recent decisions often carry {risk} risk."
            )

        if warning:
            parts.append(
                f"The recurring warning is: {warning}"
            )

        return " ".join(parts) if parts else "AURA detects early decision repetition but needs more history."

    def _strategic_drift(self, repeated_risk, repeated_warning, dynamic_reasoning, operational):
        current_warning = dynamic_reasoning.get("strategic_warning")
        scale_readiness = operational.get("scale_readiness", "")

        if repeated_risk == "high":
            return "Your decision pattern may be drifting toward aggressive moves before enough proof is built."

        if repeated_warning and current_warning and repeated_warning == current_warning:
            return "AURA detects the same strategic warning appearing repeatedly. This may indicate an unresolved core issue."

        if "Not ready" in scale_readiness or "not ready" in scale_readiness:
            return "Your business appears to be repeatedly approaching scale before operations are ready."

        return "No major strategic drift detected yet."

    def _recommended_adjustment(
        self,
        repeated_risk,
        repeated_warning,
        business_dna,
        dynamic_reasoning,
        operational,
        simulation
    ):
        trust = business_dna.get("trust_dependency")
        proof = business_dna.get("proof_requirement")
        stage = business_dna.get("business_stage")
        scale_readiness = operational.get("scale_readiness", "")
        growth_probability = simulation.get("growth_probability")
        current_priority = dynamic_reasoning.get("current_priority")

        if trust in ["high", "very_high"] or proof in ["high", "very_high"]:
            return (
                "Focus on proof before scale: testimonials, case studies, guarantees, demos, "
                "or one clear customer result should come before aggressive growth."
            )

        if repeated_risk == "high":
            return (
                "Reduce strategic risk by testing smaller, limiting spend, and proving demand before committing more resources."
            )

        if "not ready" in scale_readiness.lower():
            return (
                "Delay scaling and strengthen operations first. Build repeatable processes before increasing demand."
            )

        if stage == "early_stage" and growth_probability == "medium":
            return (
                "Keep the strategy narrow. Validate one customer segment and one offer before expanding."
            )

        return current_priority or "Keep improving the strategy using memory from repeated decisions."

    def _learning_priority(self, repeated_risk, business_dna, operational):
        stage = business_dna.get("business_stage")
        model = business_dna.get("business_model")
        scale_readiness = operational.get("scale_readiness", "")

        if repeated_risk == "high":
            return "Risk discipline"

        if "not ready" in scale_readiness.lower():
            return "Operational readiness"

        if stage == "early_stage":
            return "Validation and proof"

        if model == "digital_product_or_platform":
            return "Onboarding, retention, and repeatable acquisition"

        return "Execution consistency"


adaptive_learning_v2_engine = AdaptiveLearningV2Engine()