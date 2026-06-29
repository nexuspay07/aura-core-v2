class IntentClassificationEngine:
    """
    Phase 72

    Determines what the user is actually asking
    before the cognitive pipeline begins.

    This engine routes requests to the correct
    intelligence system.
    """

    def classify(self, goal: str):

        text = goal.lower()

        # ==========================
        # Programming
        # ==========================

        programming_keywords = [
            "python",
            "fastapi",
            "uvicorn",
            "flask",
            "django",
            "javascript",
            "typescript",
            "react",
            "nextjs",
            "node",
            "npm",
            "git",
            "github",
            "docker",
            "sql",
            "mongodb",
            "postgres",
            "api",
            "debug",
            "error",
            "exception",
            "traceback",
            "code"
        ]

        if any(word in text for word in programming_keywords):

            return {
                "intent": "programming",
                "confidence": 0.95
            }

        # ==========================
        # Business
        # ==========================

        business_keywords = [
            "profit",
            "customer",
            "startup",
            "company",
            "business",
            "marketing",
            "sales",
            "pricing",
            "clinic",
            "finance",
            "growth",
            "strategy",
            "competition"
        ]

        if any(word in text for word in business_keywords):

            return {
                "intent": "business",
                "confidence": 0.95
            }

        # ==========================
        # General Knowledge
        # ==========================

        if text.startswith("what") or text.startswith("who"):

            return {
                "intent": "knowledge",
                "confidence": 0.85
            }

        # ==========================
        # Conversation
        # ==========================

        if text in [
            "hi",
            "hello",
            "hey"
        ]:

            return {
                "intent": "conversation",
                "confidence": 0.90
            }

        return {
            "intent": "general",
            "confidence": 0.50
        }


intent_classification_engine = (
    IntentClassificationEngine()
)