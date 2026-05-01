from app.domains.business.business_domain_engine import business_domain_engine
from app.domains.business.business_strategy_engine import business_strategy_engine
from app.core.prediction_engine import prediction_engine
from app.core.strategy_comparison_engine import strategy_comparison_engine

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

        if any(x in m for x in ["low risk", "safe", "conservative"]):
            preferences["risk_tolerance"] = 0.2
        elif any(x in m for x in ["high risk", "aggressive", "fast growth"]):
            preferences["risk_tolerance"] = 0.8

        if any(x in m for x in ["competitive", "competition", "crowded market"]):
            preferences["market"] = "competitive"
        elif any(x in m for x in ["monopoly", "no competition"]):
            preferences["market"] = "monopoly"

        if any(x in m for x in ["low budget", "small budget", "cheap", "little money"]):
            preferences["budget"] = 3000
        elif any(x in m for x in ["medium budget", "normal budget", "average budget"]):
            preferences["budget"] = 10000
        elif any(x in m for x in ["high budget", "big budget", "large budget"]):
            preferences["budget"] = 50000

        return preferences

    def build_conversational_response(
        self,
        goal: str,
        best: dict,
        explanation: list,
        profile: dict | None = None
    ):
        from app.core.prediction_engine import get_market_context
        name = best.get("name", "Balanced")
        risk = best.get("risk", "medium")
        clean_goal = self.clean_goal_text(goal)

        business_intent = business_domain_engine.detect_subdomain(goal)

        preferences = self.extract_preferences(goal)
        budget = preferences.get("budget", 10000)
        market = preferences.get("market", "normal")

        market = get_market_context()

        decision_brief["market_context"] = (
        f"Current market shows {market['economy']} with "
        f"{market['consumer_behavior']} consumers. "
        f"Businesses must focus on value, efficiency, and survival strategies."
)

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
        
        

        business_strategy = business_strategy_engine.generate_strategy(
            business_intent,
            {
                "goal": goal,
                "risk": risk,
                "strategy": name,
                "budget": budget,
                "market": market
            }
        )

        prediction = prediction_engine.predict_outcome(
            business_intent,
            name,
            {
                "risk": risk,
                "budget": budget,
                "market": market
            }
        )

        strategy_comparison = strategy_comparison_engine.compare(
    business_intent,
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

        best_move = next_steps[0] if next_steps else "Start with a small test"

        confidence = prediction.get("confidence", 0.6)
        impact = prediction.get("impact", "Moderate impact expected")
        tradeoff = prediction.get("tradeoff", "Balanced risk")
        timeframe = prediction.get("timeframe", "Medium-term")
        context_note = prediction.get("context_note", "General estimate")

        # -------------------------
        # CONTEXT-AWARE DECISION LOGIC
        # -------------------------
        if market == "competitive" and budget <= 5000:
            recommended_move = "Start with a niche offer and test pricing on a small audience"
        elif market == "competitive":
            recommended_move = "Differentiate your offer and test pricing against competitors"
        elif market == "monopoly":
            recommended_move = "Set value-based pricing and maximize margins"
        elif confidence < 0.6:
            recommended_move = "Run a small test before committing"
        elif confidence > 0.75:
            recommended_move = "Execute confidently and scale faster"
        else:
            recommended_move = best_move

        # -------------------------
        # CONTEXT-AWARE FALLBACK
        # -------------------------
        if market == "competitive" and budget <= 5000:
            fallback = "If traction is low, narrow your niche further or improve your offer"
        elif market == "competitive":
            fallback = "If customers don’t convert, adjust positioning or pricing quickly"
        elif confidence < 0.5:
            fallback = "Reduce risk immediately and validate assumptions"
        else:
            fallback = self._fallback_move(name)

        decision_brief = {
            "expected_impact": impact,
            "tradeoff": tradeoff,
            "timeframe": timeframe,
            "confidence": confidence,
            "strategy_comparison": strategy_comparison,
            "recommended_move": recommended_move,
            "context_note": context_note,
            "why_this": (
                f"AURA selected the {name.lower()} approach based on your context "
                f"and predicted outcome strength."
            ),
            "main_risk": self._main_risk_message(risk),
            "watch_metric": self._watch_metric(business_intent),
            "fallback_move": fallback
        }

        return {
            "summary": f"👉 Best move: {recommended_move}",
            "detail": f"For your goal — {clean_goal}",
            "next_steps": next_steps,
            "risk_profile": risk,
            "business_intent": business_intent,
            "caution": self._risk_caution(risk),
            "decision_brief": decision_brief,
        }

    def _risk_caution(self, risk: str):
        if risk == "high":
            return "High growth potential, but this needs strong risk control."

        if risk == "low":
            return "Safer path, but growth may be slower."

        return "Balanced path between growth and risk."

    def _main_risk_message(self, risk: str):
        if risk == "high":
            return "You may move too fast before proving real demand."

        if risk == "low":
            return "You may move too slowly and miss opportunities."

        return "Execution uncertainty and weak validation."

    def _watch_metric(self, business_intent: str):
        if business_intent == "pricing":
            return "Conversion rate"

        if business_intent == "growth":
            return "Customer acquisition cost"

        if business_intent == "cost":
            return "Monthly expenses"

        if business_intent == "customer_acquisition":
            return "Lead-to-customer conversion"

        if business_intent == "hiring":
            return "Revenue or output per employee"

        if business_intent == "market_entry":
            return "Early customer demand"

        return "Customer response"

    def _fallback_move(self, strategy_name: str):
        if strategy_name == "Aggressive":
            return "Slow down and test with a smaller budget."

        if strategy_name == "Conservative":
            return "Try one faster growth channel without risking too much money."

        return "Reduce risk, validate assumptions, and test again."


conversation_engine = ConversationEngine()