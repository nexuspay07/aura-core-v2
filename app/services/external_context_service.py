"""
=========================================================

            EXTERNAL CONTEXT SERVICE

Provides real-world context for Aura.

Responsibilities

• Economic Context
• Financial Context
• Market Context
• Industry Context
• Technology Context
• News Context

Every executive decision should have
access to this service.

=========================================================
"""


class ExternalContextService:

    """
    Aura's external intelligence layer.

    Initially uses internal knowledge.

    Later versions will integrate:

    • Financial APIs
    • Economic APIs
    • News APIs
    • Market APIs
    • Search APIs
    """

    def build(

        self,

        goal: str,

        executive_analysis: dict | None = None

    ):

        goal_lower = goal.lower()

        return {

            "economy": self._economy(),

            "finance": self._finance(),

            "market": self._market(

                goal_lower

            ),

            "technology": self._technology(

                goal_lower

            ),

            "industry": self._industry(

                goal_lower

            ),

            "news": self._news(

                goal_lower

            )

        }

    # =====================================================
    # ECONOMY
    # =====================================================

    def _economy(self):

        return {

            "inflation":

                "Consumers remain price sensitive.",

            "interest_rates":

                "Higher borrowing costs continue to affect businesses.",

            "employment":

                "Labor markets remain relatively resilient.",

            "confidence":

                "Moderate"

        }

    # =====================================================
    # FINANCE
    # =====================================================

    def _finance(self):

        return {

            "capital_environment":

                "Investors prioritize profitable businesses.",

            "venture_capital":

                "Funding is available but more selective.",

            "credit":

                "Business financing remains accessible with strong fundamentals."

        }

    # =====================================================
    # MARKET
    # =====================================================

    def _market(

        self,

        goal

    ):

        if "ai" in goal:

            return {

                "outlook":

                    "High-growth market.",

                "competition":

                    "Very high.",

                "trend":

                    "Rapid enterprise AI adoption."

            }

        if "logistics" in goal:

            return {

                "outlook":

                    "Stable demand.",

                "competition":

                    "High.",

                "trend":

                    "Automation and route optimization."

            }

        return {

            "outlook":

                "Moderate.",

            "competition":

                "Unknown.",

            "trend":

                "Validate customer demand."

        }

    # =====================================================
    # TECHNOLOGY
    # =====================================================

    def _technology(

        self,

        goal

    ):

        return {

            "ai":

                "AI adoption continues to accelerate.",

            "automation":

                "Businesses continue automating operations.",

            "cloud":

                "Cloud-native platforms dominate new deployments."

        }

    # =====================================================
    # INDUSTRY
    # =====================================================

    def _industry(

        self,

        goal

    ):

        return {

            "maturity":

                "Growing",

            "innovation":

                "High",

            "digitalization":

                "Increasing"

        }

    # =====================================================
    # NEWS
    # =====================================================

    def _news(

        self,

        goal

    ):

        return [

            "No live news provider connected yet."

        ]


external_context_service = (
    ExternalContextService()
)