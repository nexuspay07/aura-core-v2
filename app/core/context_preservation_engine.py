class ContextPreservationEngine:
    """
    Phase 65.1

    Preserves business identity and strategic
    context throughout the Aura pipeline.

    Prevents engines from losing:

    - industry
    - business_model
    - business_stage
    - customer_type
    - primary_channel
    """

    def preserve(
        self,
        goal: str,
        strategic_analysis: dict,
        market_intelligence: dict,
        competitive_intelligence: dict
    ):

        industry = (
            strategic_analysis.get(
                "business_model",
                "general_business"
            )
        )

        business_stage = (
            strategic_analysis.get(
                "business_stage",
                "unknown_stage"
            )
        )

        customer_type = self._detect_customer_type(
            industry,
            goal
        )

        primary_channel = self._detect_channel(
            industry,
            goal
        )

        return {

            "industry":
                industry,

            "business_model":
                industry,

            "business_stage":
                business_stage,

            "customer_type":
                customer_type,

            "primary_channel":
                primary_channel,

            "market_type":
                market_intelligence.get(
                    "market_type",
                    "general"
                ),

            "competition_level":
                market_intelligence.get(
                    "competition_level",
                    "unknown"
                ),

            "recommended_moat":
                competitive_intelligence.get(
                    "recommended_moat",
                    "unknown"
                )
        }

    def _detect_customer_type(
        self,
        industry,
        goal
    ):

        goal_lower = goal.lower()

        if industry == "healthcare":
            return "patients"

        if industry == "finance":
            return "clients"

        if industry == "logistics":
            return "shippers"

        if industry == "saas":
            return "software_users"

        if industry == "ai":
            return "business_users"

        if "customer" in goal_lower:
            return "customers"

        return "general_customers"

    def _detect_channel(
        self,
        industry,
        goal
    ):

        goal_lower = goal.lower()

        if industry == "saas":
            return "online"

        if industry == "ai":
            return "online"

        if industry == "healthcare":
            return "offline"

        if industry == "real_estate":
            return "offline"

        if industry == "logistics":
            return "hybrid"

        if "website" in goal_lower:
            return "online"

        return "hybrid"


context_preservation_engine = (
    ContextPreservationEngine()
)