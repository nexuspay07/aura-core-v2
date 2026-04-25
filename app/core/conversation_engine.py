from app.domains.business.business_domain_engine import business_domain_engine
from app.domains.business.business_strategy_engine import business_strategy_engine
from app.core.prediction_engine import prediction_engine


class ConversationEngine:

    def detect_intent(self, message: str):
        m = message.lower()

        if any(x in m for x in [
            "pain", "fever", "cough", "headache", "fatigue",
            "shortness of breath", "dizziness", "symptom", "medical", "health"
        ]):
            return "healthcare_strategy"

        if any(x in m for x in [
            "grow", "startup", "business", "company", "scale",
            "customers", "revenue", "pricing", "price", "hire",
            "market", "cost", "expenses", "sales", "clients"
        ]):
            return "business_strategy"

        if any(x in m for x in [
            "invest", "money", "portfolio", "budget", "finance", "returns"
        ]):
            return "finance_strategy"

        return "general"

    def needs_clarification(self, message: str):
        return len(message.strip().split()) <= 3

    def build_clarification_question(self, intent: str):
        if intent == "business_strategy":
            return "Do you want fast growth, low-risk growth, pricing help, customer acquisition, or cost control?"

        if intent == "healthcare_strategy":
            return "What symptom are you experiencing and how severe is it?"

        if intent == "finance_strategy":
            return "Are you looking for safer returns, balanced growth, or aggressive upside?"

        return "Can you clarify your goal?"

    def detect_business_subdomain(self, message: str):
        return business_domain_engine.detect_subdomain(message)

    def clean_goal_text(self, goal: str):
        cleaned = goal.strip()

        prefixes = [
            "I want to ",
            "i want to ",
            "I need to ",
            "i need to ",
            "I would like to ",
            "i would like to ",
        ]

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned.replace(prefix, "", 1).strip()

        return cleaned

    def extract_preferences(self, message: str):
        m = message.lower()

        preferences = {
            "risk_tolerance": 0.5,
            "budget": 10000,
            "market": "normal"
        }

        if "low risk" in m or "safe" in m or "conservative" in m:
            preferences["risk_tolerance"] = 0.2
        elif "high risk" in m or "aggressive" in m or "fast growth" in m:
            preferences["risk_tolerance"] = 0.8
        elif "balanced" in m or "moderate risk" in m:
            preferences["risk_tolerance"] = 0.5

        if "competitive" in m:
            preferences["market"] = "competitive"
        elif "monopoly" in m:
            preferences["market"] = "monopoly"

        if "small budget" in m or "low budget" in m:
            preferences["budget"] = 3000
        elif "large budget" in m or "big budget" in m:
            preferences["budget"] = 50000

        return preferences

    def build_conversational_response(
        self,
        goal: str,
        best: dict,
        explanation: list,
        profile: dict | None = None
    ):
        name = best.get("name", "Balanced")
        risk = best.get("risk", "medium")
        clean_goal = self.clean_goal_text(goal)

        business_intent = business_domain_engine.detect_subdomain(goal)

        business_strategy = business_strategy_engine.generate_strategy(
            business_intent,
            {
                "goal": goal,
                "risk": risk,
                "strategy": name
            }
        )

        prediction = prediction_engine.predict_outcome(
            business_intent,
            name,
            {
                "risk": risk
            }
        )

        simple_advice = business_strategy.get(
            "advice",
            "Start small, validate your idea, and grow based on real demand."
        )

        next_steps = business_strategy.get("steps", [
            "Start with one small test",
            "Measure the result",
            "Only scale after proof"
        ])

        best_move = next_steps[0] if next_steps else "Start small and test"

        decision_brief = {
            "recommended_move": best_move,
            "why_this": (
                "This approach works because it balances growth and risk. "
                "It gives you a higher chance of success without overcommitting resources early."
            ),
            "main_risk": self._main_risk_message(risk),
            "watch_metric": self._watch_metric(business_intent),
            "fallback_move": self._fallback_move(name),
            "expected_impact": prediction.get("impact"),
            "tradeoff": prediction.get("tradeoff"),
            "timeframe": prediction.get("timeframe"),
            "confidence": prediction.get("confidence")
        }

        memory_note = ""
        if profile and profile.get("interaction_count", 0) >= 2:
            preferred_risk = profile.get("preferred_risk")
            if preferred_risk == "low":
                memory_note = "Since you usually prefer safer decisions, "
            elif preferred_risk == "high":
                memory_note = "Since you usually prefer faster growth, "

        summary = (
            f"{memory_note}{simple_advice}\n\n"
            f"👉 Best move: {best_move}"
        )

        detail = (
            f"For your goal — {clean_goal} — AURA recommends a {name.lower()} approach."
        )

        advanced_details = {
            "strategy": name,
            "risk": risk,
            "business_intent": business_intent,
            "final_score": best.get("final_score"),
            "decision_score": best.get("decision_score"),
            "trust_score": best.get("trust_score"),
            "failure_probability": best.get("failure_probability"),
            "explanation": explanation
        }

        return {
            "summary": summary,
            "detail": detail,
            "next_steps": next_steps,
            "risk_profile": risk,
            "business_intent": business_intent,
            "caution": self._risk_caution(risk),
            "decision_brief": decision_brief,
            "advanced_details": advanced_details
        }

    def _risk_caution(self, risk: str):
        if risk == "high":
            return "This path can grow fast, but it needs strong risk control."

        if risk == "low":
            return "This path is safer, but growth may be slower."

        return "This path balances growth and risk."

    def _main_risk_message(self, risk: str):
        if risk == "high":
            return "You may spend too much or move too fast before proving that customers actually want it."

        if risk == "low":
            return "You may grow too slowly and allow competitors or opportunities to pass you."

        return "You may spend time and money before confirming real demand."

    def _watch_metric(self, business_intent: str):
        if business_intent == "pricing":
            return "How many people actually buy after seeing your price"

        if business_intent == "growth":
            return "How much it costs to get one real customer"

        if business_intent == "cost":
            return "Whether monthly expenses are going down without hurting sales"

        if business_intent == "acquisition":
            return "How many qualified leads turn into real customers"

        if business_intent == "hiring":
            return "Whether the new hire increases output or revenue"

        if business_intent == "market_entry":
            return "Whether early customers show real demand"

        return "Whether people show real interest or actually buy"

    def _fallback_move(self, strategy_name: str):
        if strategy_name == "Aggressive":
            return "If results are unstable, slow down and test with a smaller budget."

        if strategy_name == "Conservative":
            return "If progress is too slow, test one faster growth channel without risking too much money."

        return "If results are unclear, reduce spending and run a smaller experiment."


conversation_engine = ConversationEngine()