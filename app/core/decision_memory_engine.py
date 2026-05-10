from datetime import datetime, timezone


class DecisionMemoryEngine:
    def __init__(self):
        self.memory = {}

    def save_decision(
        self,
        session_id: str,
        goal: str,
        pipeline_result: dict,
        response: dict | None = None
    ):
        session_id = session_id or "default"
        response = response or {}

        business_dna = pipeline_result.get("business_dna", {})
        dynamic_reasoning = pipeline_result.get("dynamic_reasoning", {})
        prediction = pipeline_result.get("prediction", {})
        best_strategy = pipeline_result.get("best_strategy", {})
        strategic_simulation = pipeline_result.get("strategic_simulation", {})

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal": goal,
            "business_model": business_dna.get("business_model"),
            "business_stage": business_dna.get("business_stage"),
            "market": business_dna.get("market"),
            "competition_pressure": business_dna.get("competition_pressure"),
            "trust_dependency": business_dna.get("trust_dependency"),
            "scalability": business_dna.get("scalability"),
            "recommended_strategy": best_strategy.get("name"),
            "risk": best_strategy.get("risk"),
            "decision_score": best_strategy.get("decision_score"),
            "failure_probability": best_strategy.get("failure_probability"),
            "current_bottleneck": dynamic_reasoning.get("current_bottleneck"),
            "growth_blocker": dynamic_reasoning.get("growth_blocker"),
            "strategic_warning": dynamic_reasoning.get("strategic_warning"),
            "prediction_confidence": prediction.get("confidence"),
            "growth_probability": strategic_simulation.get("growth_probability"),
            "failure_probability_label": strategic_simulation.get("failure_probability"),
            "recommended_move": response.get("decision_brief", {}).get("recommended_move"),
        }

        self.memory.setdefault(session_id, []).append(record)

        return record

    def get_history(self, session_id: str, limit: int = 10):
        session_id = session_id or "default"
        return self.memory.get(session_id, [])[-limit:]

    def summarize_history(self, session_id: str):
        history = self.get_history(session_id, limit=20)

        if not history:
            return {
                "has_memory": False,
                "total_decisions": 0,
                "summary": "No previous decision memory found.",
                "repeated_business_model": None,
                "repeated_risk": None,
                "repeated_warning": None,
                "memory_insight": None,
            }

        business_models = {}
        risks = {}
        warnings = {}

        for item in history:
            model = item.get("business_model")
            risk = item.get("risk")
            warning = item.get("strategic_warning")

            if model:
                business_models[model] = business_models.get(model, 0) + 1

            if risk:
                risks[risk] = risks.get(risk, 0) + 1

            if warning:
                warnings[warning] = warnings.get(warning, 0) + 1

        repeated_business_model = self._top_item(business_models)
        repeated_risk = self._top_item(risks)
        repeated_warning = self._top_item(warnings)

        memory_insight = self._build_memory_insight(
            len(history),
            repeated_business_model,
            repeated_risk,
            repeated_warning
        )

        return {
            "has_memory": True,
            "total_decisions": len(history),
            "summary": f"AURA has memory of {len(history)} previous decision(s) in this session.",
            "repeated_business_model": repeated_business_model,
            "repeated_risk": repeated_risk,
            "repeated_warning": repeated_warning,
            "memory_insight": memory_insight,
            "recent_decisions": history[-5:],
        }

    def _top_item(self, counts: dict):
        if not counts:
            return None

        return sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[0][0]

    def _build_memory_insight(
        self,
        total: int,
        business_model,
        risk,
        warning
    ):
        parts = []

        if business_model:
            parts.append(
                f"You have repeatedly explored {business_model.replace('_', ' ')} decisions."
            )

        if risk:
            parts.append(
                f"Your recent recommendations have mostly carried {risk} risk."
            )

        if warning:
            parts.append(
                f"A recurring warning is: {warning}"
            )

        if not parts:
            return "AURA is beginning to learn your decision pattern."

        return " ".join(parts)


decision_memory_engine = DecisionMemoryEngine()