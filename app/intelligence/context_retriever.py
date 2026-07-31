class ContextRetriever:
    """
    =====================================================

                CONTEXT RETRIEVER

    This component gathers every piece of
    information Aura needs BEFORE reasoning.

    It does NOT make decisions.

    It simply builds the world's current state.

    Future Context Sources

    ✓ Business Profile

    ✓ Organization

    ✓ Workspace

    ✓ Memory

    ✓ Market

    ✓ Economy

    ✓ Finance

    ✓ News

    ✓ Industry

    ✓ Regulations

    =====================================================
    """

    def retrieve(

        self,

        entities: dict,

        user_context: dict | None = None

    ):

        user_context = user_context or {}

        return {

            # -------------------------
            # USER
            # -------------------------

            "organization":

                user_context.get(

                    "organization",

                    {}

                ),

            "workspace":

                user_context.get(

                    "workspace",

                    {}

                ),

            "business_profile":

                user_context.get(

                    "business_profile",

                    {}

                ),

            # -------------------------
            # MEMORY
            # -------------------------

            "memory": {

                "previous_questions": [],

                "previous_recommendations": [],

                "known_business_facts": {}

            },

            # -------------------------
            # MARKET
            # -------------------------

            "market": {

                "industry":

                    entities.get(

                        "industry"

                    ),

                "competition":

                    "unknown",

                "market_size":

                    "unknown",

                "growth_rate":

                    "unknown"

            },

            # -------------------------
            # ECONOMY
            # -------------------------

            "economy": {

                "country":

                    entities.get(

                        "location"

                    ),

                "inflation":

                    "unknown",

                "interest_rate":

                    "unknown",

                "consumer_spending":

                    "unknown"

            },

            # -------------------------
            # FINANCE
            # -------------------------

            "finance": {

                "available_capital":

                    entities.get(

                        "capital"

                    ),

                "cashflow":

                    None,

                "budget":

                    entities.get(

                        "capital"

                    )

            },

            # -------------------------
            # NEWS
            # -------------------------

            "news": [],

            # -------------------------
            # ENTITIES
            # -------------------------

            "entities": entities

        }


context_retriever = ContextRetriever()