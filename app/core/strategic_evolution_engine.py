class StrategicEvolutionEngine:
    """
    Strategic Evolution Engine

    This engine studies decision memory and detects how the user's
    strategy pattern is evolving over time.
    """

    def analyze(self, memory_summary: dict, current_pipeline: dict | None = None):
        current_pipeline = current_pipeline or {}

        history = memory_summary.get("recent_decisions", []) if memory_summary else []
        total = memory_summary.get("total_decisions", 0) if memory_summary else 0

        if not history:
            return {
                "evolution_active": False,
                "dominant_strategy_pattern": "Not enough memory yet.",
                "risk_drift": "Unknown",
                "strategic_stability": "Unknown",
                "repeated_failure_pattern": "No repeated failure pattern detected yet.",
                "strategic_adaptation": "AURA needs more decision history before evolving strategy.",
                "evolution_recommendation": "Ask more related business questions so AURA can learn strategy patterns.",
            }

        strategies = self._count_values(history, "recommended_strategy")
        risks = self._count_values(history, "risk")
        warnings = self._count_values(history, "strategic_warning")
        failure_labels = self._count_values(history, "failure_probability_label")

        dominant_strategy = self._top_item(strategies)
        dominant_risk = self._top_item(risks)
        dominant_warning = self._top_item(warnings)
        dominant_failure = self._top_item(failure_labels)

        business_dna = current_pipeline.get("business_dna", {})
        operational = current_pipeline.get("operational_intelligence", {})
        dynamic_reasoning = current_pipeline.get("dynamic_reasoning", {})

        risk_drift = self._risk_drift(history, dominant_risk)
        stability = self._strategic_stability(strategies, risks, total)
        repeated_failure = self._repeated_failure_pattern(
            dominant_warning,
            dominant_failure
        )

        adaptation = self._strategic_adaptation(
            dominant_strategy,
            dominant_risk,
            dominant_warning,
            business_dna,
            operational,
            dynamic_reasoning
        )

        recommendation = self._evolution_recommendation(
            dominant_strategy,
            dominant_risk,
            dominant_warning,
            operational
        )

        return {
            "evolution_active": True,
            "total_decisions_analyzed": total,
            "dominant_strategy_pattern": dominant_strategy or "Unknown",
            "dominant_risk_pattern": dominant_risk or "Unknown",
            "dominant_warning_pattern": dominant_warning or "None",
            "dominant_failure_pattern": dominant_failure or "Unknown",
            "risk_drift": risk_drift,
            "strategic_stability": stability,
            "repeated_failure_pattern": repeated_failure,
            "strategic_adaptation": adaptation,
            "evolution_recommendation": recommendation,
        }

    def _count_values(self, history, key):
        counts = {}

        for item in history:
            value = item.get(key)

            if value:
                counts[value] = counts.get(value, 0) + 1

        return counts

    def _top_item(self, counts):
        if not counts:
            return None

        return sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[0][0]

    def _risk_drift(self, history, dominant_risk):
        if len(history) < 3:
            return "Early pattern — more history needed."

        recent_risks = [x.get("risk") for x in history[-3:] if x.get("risk")]

        if not recent_risks:
            return "Unknown risk drift."

        if all(r == "high" for r in recent_risks):
            return "Risk is drifting high. AURA should recommend stronger validation and smaller tests."

        if all(r == "low" for r in recent_risks):
            return "Risk is staying low. Growth may be safe but possibly slow."

        if "high" in recent_risks and "low" in recent_risks:
            return "Risk pattern is unstable. AURA should balance ambition with clearer proof."

        return f"Risk pattern is mostly {dominant_risk or 'mixed'}."

    def _strategic_stability(self, strategies, risks, total):
        if total < 3:
            return "Low confidence — not enough history."

        if len(strategies) == 1 and len(risks) == 1:
            return "Stable — user strategy pattern is consistent."

        if len(strategies) <= 2:
            return "Moderate — strategy pattern is forming."

        return "Unstable — user is exploring many strategic directions."

    def _repeated_failure_pattern(self, warning, failure):
        if warning:
            return f"Recurring strategic warning detected: {warning}"

        if failure:
            return f"Recurring failure probability pattern: {failure}"

        return "No repeated failure pattern detected yet."

    def _strategic_adaptation(
        self,
        strategy,
        risk,
        warning,
        business_dna,
        operational,
        dynamic_reasoning
    ):
        proof = business_dna.get("proof_requirement")
        trust = business_dna.get("trust_dependency")
        scale_readiness = operational.get("scale_readiness", "")
        bottleneck = dynamic_reasoning.get("current_bottleneck")

        if risk == "high":
            return "AURA should adapt toward safer validation-first recommendations until stronger proof exists."

        if proof in ["high", "very_high"] or trust in ["high", "very_high"]:
            return "AURA should prioritize proof-building, trust signals, and customer validation before recommending scale."

        if "not ready" in scale_readiness.lower():
            return "AURA should delay scaling recommendations and focus on operational readiness."

        if bottleneck:
            return f"AURA should adapt future strategy around this bottleneck: {bottleneck}"

        if strategy:
            return f"AURA should continue refining the {strategy} pattern while watching for repeated weaknesses."

        return "AURA should continue learning from future decisions."

    def _evolution_recommendation(
        self,
        strategy,
        risk,
        warning,
        operational
    ):
        scale_readiness = operational.get("scale_readiness", "")

        if warning:
            return f"Resolve the recurring warning before increasing business complexity: {warning}"

        if risk == "high":
            return "Run smaller experiments, lower spending exposure, and require proof before scaling."

        if "not ready" in scale_readiness.lower():
            return "Build repeatable operations before increasing customer acquisition."

        if strategy == "Aggressive":
            return "Aggressive strategy should only continue if proof, retention, and operations are strong."

        if strategy == "Conservative":
            return "Conservative strategy is safe, but AURA should watch for missed growth opportunities."

        return "Continue improving the strategy using memory, simulation, and operational feedback."


strategic_evolution_engine = StrategicEvolutionEngine()