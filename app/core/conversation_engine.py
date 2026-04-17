class ConversationEngine:
    def detect_intent(self, message: str):
        message_lower = message.lower()

        if any(word in message_lower for word in ["start", "grow", "scale", "business", "startup"]):
            return "business_strategy"

        if any(word in message_lower for word in ["invest", "portfolio", "money", "finance", "budget"]):
            return "finance_strategy"

        if any(word in message_lower for word in ["help", "what should i do", "advice"]):
            return "advice"

        return "general"

    def needs_clarification(self, message: str):
        short_message = len(message.strip().split()) <= 3
        vague_terms = ["grow business", "make money", "help me", "improve things"]

        if short_message:
            return True

        if message.lower().strip() in vague_terms:
            return True

        return False

    def build_clarification_question(self, intent: str):
        if intent == "business_strategy":
            return "Do you want fast growth, low-risk growth, or long-term stable growth?"

        if intent == "finance_strategy":
            return "Are you trying to grow money safely, aggressively, or with balanced risk?"

        return "Can you give me a bit more detail about your goal?"

    def extract_goal(self, message: str):
        return message.strip()

    def build_conversational_response(self, goal: str, best_strategy: dict, explanation: list):
        strategy_name = best_strategy.get("name", "Unknown")
        risk = best_strategy.get("risk", "unknown")
        next_move = ""

        if strategy_name == "Aggressive":
            next_move = "move quickly, invest in growth, and act before competitors react"
        elif strategy_name == "Balanced":
            next_move = "scale carefully, validate what works, and grow without losing control"
        elif strategy_name == "Conservative":
            next_move = "protect cash, reduce risk, and grow in a stable way"

        summary = (
            f"For your goal '{goal}', AURA recommends a {risk}-risk {strategy_name.lower()} strategy. "
            f"The main idea is to {next_move}."
        )

        detail = explanation[0] if explanation else "AURA selected this based on overall risk-adjusted performance."

        return {
            "summary": summary,
            "detail": detail
        }


conversation_engine = ConversationEngine()