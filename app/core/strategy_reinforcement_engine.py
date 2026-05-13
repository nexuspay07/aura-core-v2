class StrategyReinforcementEngine:
    """
    Strategy Reinforcement Engine

    This engine studies decision memory and gives reinforcement signals.
    It rewards stable, lower-risk, proof-based strategy patterns and warns
    against repeated high-risk or unresolved failure patterns.
    """

    def analyze(self, memory_summary: dict, strategic_evolution: dict | None = None):
        strategic_evolution = strategic_evolution or {}

        history = memory_summary.get("recent_decisions", []) if memory_summary else []
        total = memory_summary.get("total_decisions", 0) if memory_summary else 0

        if not history:
            return {
                "reinforcement_active": False,
                "strategy_reward_score": 0,
                "reinforcement_signal": "Not enough memory to reinforce strategy yet.",
                "strategy_bias": "neutral",
                "penalized_pattern": None,
                "rewarded_pattern": None,
                "reinforcement_recommendation": "Build more decision history first."
            }

        risks = [x.get("risk") for x in history if x.get("risk")]
        strategies = [x.get("recommended_strategy") for x in history if x.get("recommended_strategy")]
        warnings = [x.get("strategic_warning") for x in history if x.get("strategic_warning")]

        reward_score = self._reward_score(risks, warnings, strategic_evolution)
        bias = self._strategy_bias(reward_score, risks)
        penalized = self._penalized_pattern(risks, warnings, strategic_evolution)
        rewarded = self._rewarded_pattern(strategies, risks)
        signal = self._reinforcement_signal(reward_score, bias, penalized, rewarded)
        recommendation = self._recommendation(reward_score, bias, penalized)

        return {
            "reinforcement_active": True,
            "total_decisions_analyzed": total,
            "strategy_reward_score": reward_score,
            "reinforcement_signal": signal,
            "strategy_bias": bias,
            "penalized_pattern": penalized,
            "rewarded_pattern": rewarded,
            "reinforcement_recommendation": recommendation
        }

    def _reward_score(self, risks, warnings, strategic_evolution):
        score = 50

        high_count = risks.count("high")
        medium_count = risks.count("medium")
        low_count = risks.count("low")

        score -= high_count * 12
        score += low_count * 8
        score += medium_count * 4

        if warnings:
            score -= min(len(warnings) * 6, 24)

        stability = strategic_evolution.get("strategic_stability", "")
        risk_drift = strategic_evolution.get("risk_drift", "")

        if "Stable" in stability:
            score += 10

        if "Unstable" in stability:
            score -= 10

        if "drifting high" in risk_drift.lower():
            score -= 15

        if "staying low" in risk_drift.lower():
            score += 8

        return max(0, min(100, round(score, 2)))

    def _strategy_bias(self, score, risks):
        if score >= 75:
            return "growth_confident"

        if score >= 55:
            return "balanced_validation"

        if risks.count("high") >= 2:
            return "risk_reduction"

        return "validation_first"

    def _penalized_pattern(self, risks, warnings, strategic_evolution):
        if risks.count("high") >= 2:
            return "Repeated high-risk strategy pattern"

        repeated_failure = strategic_evolution.get("repeated_failure_pattern")
        if repeated_failure and repeated_failure != "No repeated failure pattern detected yet.":
            return repeated_failure

        if warnings:
            return "Repeated unresolved strategic warnings"

        return None

    def _rewarded_pattern(self, strategies, risks):
        if risks.count("low") >= 2:
            return "Repeated low-risk disciplined execution"

        if risks.count("medium") >= 2:
            return "Repeated balanced strategy behavior"

        if strategies:
            top_strategy = max(set(strategies), key=strategies.count)
            return f"Repeated use of {top_strategy} strategy"

        return None

    def _reinforcement_signal(self, score, bias, penalized, rewarded):
        if penalized:
            return f"AURA is penalizing this pattern: {penalized}"

        if score >= 75:
            return "AURA is reinforcing this strategy pattern because recent decisions look stable."

        if rewarded:
            return f"AURA is reinforcing: {rewarded}"

        if bias == "validation_first":
            return "AURA is shifting toward validation-first guidance until stronger proof exists."

        return "AURA is keeping a balanced reinforcement signal."

    def _recommendation(self, score, bias, penalized):
        if penalized:
            return "Reduce exposure, test smaller, and resolve the repeated strategic warning before scaling."

        if bias == "growth_confident":
            return "Growth can be explored, but continue watching operational readiness and customer proof."

        if bias == "balanced_validation":
            return "Continue balanced testing while improving proof, customer clarity, and execution systems."

        if bias == "risk_reduction":
            return "AURA should reduce aggressive recommendations and prioritize safer validation steps."

        return "Focus on proving demand before scaling investment."


strategy_reinforcement_engine = StrategyReinforcementEngine()