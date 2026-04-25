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

    # --------------------------
    # SMART QUESTION SYSTEM
    # --------------------------
    def missing_context(self, preferences: dict):
        missing = []

        if preferences.get("budget") == 10000:
            missing.append("budget")

        if preferences.get("market") == "normal":
            missing.append("market")

        return missing

    def build_context_question(self, missing: list):
        questions = []

        if "budget" in missing:
            questions.append("What is your budget? (low, medium, high)")

        if "market" in missing:
            questions.append("Is your market competitive or not?")

        return "To give a more accurate answer, I need:\n\n• " + "\n• ".join(questions)

    # --------------------------
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

    # --------------------------
    # FIXED PREFERENCES
    # --------------------------
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

        # MARKET
        if any(x in m for x in ["competitive", "competition", "crowded market"]):
            preferences["market"] = "competitive"
        elif any(x in m for x in ["monopoly", "no competition"]):
            preferences["market"] = "monopoly"

        # BUDGET
        if any(x in m for x in ["low budget", "small budget", "cheap", "little money"]):
            preferences["budget"] = 3000
        elif any(x in m for x in ["high budget", "big budget", "large budget"]):
            preferences["budget"] = 50000

        return preferences

    # --------------------------
    # MAIN RESPONSE ENGINE
    # --------------------------
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

        # CONTEXT
        preferences = self.extract_preferences(goal)
        budget = preferences.get("budget", 10000)
        market = preferences.get("market", "normal")

        # 🔥 SMART QUESTIONS TRIGGER
        missing = self.missing_context(preferences)
        if missing:
            return {
                "summary": self.build_context_question(missing),
                "detail": "AURA needs more information before making a decision.",
                "next_steps": [],
                "risk_profile": "unknown",
                "business_intent": business_intent,
                "caution": "",
                "decision_brief": {},
            }

        # STRATEGY
        business_strategy = business_strategy_engine.generate_strategy(
            business_intent,
            {
                "goal": goal,
                "risk": risk,
                "strategy": name
            }
        )

        # PREDICTION
        prediction = prediction_engine.predict_outcome(
            business_intent,
            name,
            {
                "risk": risk,
                "budget": budget,
                "market": market
            }
        )

        next_steps = business_strategy.get("steps", [
            "Start small",
            "Measure results",
            "Scale if it works"
        ])

        best_move = next_steps[0]

        decision_brief = {
            "recommended_move": best_move,
            "why_this": "This balances growth and risk.",
            "main_risk": self._main_risk_message(risk),
            "watch_metric": self._watch_metric(business_intent),
            "fallback_move": self._fallback_move(name),
            "expected_impact": prediction.get("impact"),
            "tradeoff": prediction.get("tradeoff"),
            "timeframe": prediction.get("timeframe"),
            "confidence": prediction.get("confidence"),
            "context_note": prediction.get("context_note")
        }

        return {
            "summary": f"👉 Best move: {best_move}",
            "detail": f"For your goal — {clean_goal}",
            "next_steps": next_steps,
            "risk_profile": risk,
            "business_intent": business_intent,
            "caution": self._risk_caution(risk),
            "decision_brief": decision_brief,
        }

    # --------------------------
    def _risk_caution(self, risk: str):
        if risk == "high":
            return "High growth but risky."
        if risk == "low":
            return "Safer but slower."
        return "Balanced."

    def _main_risk_message(self, risk: str):
        if risk == "high":
            return "You may move too fast."
        if risk == "low":
            return "You may move too slow."
        return "Execution uncertainty."

    def _watch_metric(self, business_intent: str):
        if business_intent == "pricing":
            return "Conversion rate"
        if business_intent == "growth":
            return "Customer acquisition cost"
        return "Customer response"

    def _fallback_move(self, strategy_name: str):
        if strategy_name == "Aggressive":
            return "Slow down and test smaller."
        if strategy_name == "Conservative":
            return "Try one faster channel."
        return "Reduce risk and test again."


conversation_engine = ConversationEngine()