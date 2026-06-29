class ProgrammingIntelligenceEngine:
    """
    Phase 72

    Programming Intelligence Engine

    Handles programming, debugging,
    software engineering and technical
    questions separately from the
    Business Intelligence Pipeline.
    """

    def analyze(
        self,
        goal: str
    ):

        text = goal.lower()

        # ======================================
        # FastAPI
        # ======================================

        if "uvicorn" in text:

            return {
                "category": "FastAPI",

                "summary": (
                    "This command starts a FastAPI "
                    "application using the Uvicorn "
                    "ASGI server."
                ),

                "recommendation": (
                    "Verify that the virtual environment "
                    "is activated and all dependencies "
                    "are installed before running it."
                )
            }

        # ======================================
        # Git
        # ======================================

        if "git" in text:

            return {
                "category": "Git",

                "summary": (
                    "Git command detected."
                ),

                "recommendation": (
                    "Review repository status before "
                    "executing destructive commands."
                )
            }

        # ======================================
        # Python
        # ======================================

        if "python" in text:

            return {
                "category": "Python",

                "summary": (
                    "Python-related request detected."
                ),

                "recommendation": (
                    "Inspect the code, identify the "
                    "error, and verify installed "
                    "packages and environment."
                )
            }

        # ======================================
        # Default
        # ======================================

        return {

            "category": "Programming",

            "summary": (
                "Programming request detected."
            ),

            "recommendation": (
                "Further technical analysis required."
            )
        }


programming_intelligence_engine = (
    ProgrammingIntelligenceEngine()
)