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

    # ✅ FIXED FUNCTION (this was broken before)
    def extract_preferences(self, message: str):
        m = message.lower()

        preferences = {
            "risk_tolerance": 0.5,
            "budget": 10000,
            "market": "normal"
        }

        # RISK
        if any(x in m for x in ["low risk", "safe", "conservative"]):
            preferences["risk_tolerance"] = 0.2
        elif any(x in m for x in ["high risk", "aggressive", "fast growth"]):
            preferences["risk_tolerance"] = 0.8
        elif any(x in m for x in ["balanced", "moderate risk"]):
            preferences["risk_tolerance"] = 0.5

        # MARKET
        if any(x in m for x in ["competitive", "competition", "crowded market"]):
            preferences["market"] = "competitive"
        elif any(x in m for x in ["monopoly", "no competition"]):
            preferences["market"] = "monopoly"

        # BUDGET
        if any(x in m for x in ["low budget", "small budget", "cheap", "little money", "not much money"]):
            preferences["budget"] = 3000
        elif any(x in m for x in ["high budget", "big budget", "large budget", "a lot of money"]):
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

        # ✅ CONTEXT-AWARE FIX
        preferences = self.extract_preferences(goal)
        budget = preferences.get("budget", 10000)
        market = preferences.get("market", "normal")

        prediction = prediction_engine.predict_outcome(
            business_intent,
            name,
            {
                "risk": risk,
                "budget": budget,
                "market": market
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
            "confidence": prediction.get("confidence"),
            "context_note": prediction.get("context_note")  # ✅ ADDED
        }

        summary = f"{simple_advice}\n\n👉 Best move: {best_move}"

        detail = f"For your goal — {clean_goal} — AURA recommends a {name.lower()} approach."

        return {
            "summary": summary,
            "detail": detail,
            "next_steps": next_steps,
            "risk_profile": risk,
            "business_intent": business_intent,
            "caution": self._risk_caution(risk),
            "decision_brief": decision_brief,
        }

    def _risk_caution(self, risk: str):
        if risk == "high":
            return "This path can grow fast, but it needs strong risk control."
        if risk == "low":
            return "This path is safer, but growth may be slower."
        return "This path balances growth and risk."

    def _main_risk_message(self, risk: str):
        if risk == "high":
            return "You may spend too much or move too fast before proving demand."
        if risk == "low":
            return "You may grow too slowly and miss opportunities."
        return "You may spend time and money before confirming demand."

    def _watch_metric(self, business_intent: str):
        if business_intent == "pricing":
            return "How many people buy after seeing your price"
        if business_intent == "growth":
            return "Customer acquisition cost"
        if business_intent == "cost":
            return "Monthly expenses"
        return "Customer response"

    def _fallback_move(self, strategy_name: str):
        if strategy_name == "Aggressive":
            return "If unstable, slow down and test smaller."
        if strategy_name == "Conservative":
            return "If too slow, test one faster channel."
        return "Reduce spending and run smaller tests."


conversation_engine = ConversationEngine()