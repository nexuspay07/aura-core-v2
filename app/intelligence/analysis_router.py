class AnalysisRouter:
    """
    =====================================================

                ANALYSIS ROUTER

    The Analysis Router decides which
    intelligence engines should execute.

    It is Aura's traffic controller.

    It does NOT perform analysis.

    It only builds the execution plan.

    =====================================================
    """

    def build_plan(

        self,

        entities: dict,

        context: dict

    ):

        plan = []

        intent = entities.get("intent")

        industry = entities.get("industry")

        capital = entities.get("capital")

        # ------------------------------------
        # Always Required
        # ------------------------------------

        plan.extend([

            "business_understanding",

            "strategic_analysis",

            "market_intelligence"

        ])

        # ------------------------------------
        # Startup Decisions
        # ------------------------------------

        if intent == "startup":

            plan.extend([

                "prediction",

                "deep_reasoning",

                "operational_intelligence"

            ])

        # ------------------------------------
        # Growth Decisions
        # ------------------------------------

        elif intent == "growth":

            plan.extend([

                "prediction",

                "strategic_simulation",

                "competitive_intelligence"

            ])

        # ------------------------------------
        # Investment Decisions
        # ------------------------------------

        elif intent == "investment":

            plan.extend([

                "prediction",

                "competitive_intelligence",

                "deep_reasoning"

            ])

        # ------------------------------------
        # Capital Analysis
        # ------------------------------------

        if capital is not None:

            plan.append(

                "financial_analysis"

            )

        # ------------------------------------
        # AI Businesses
        # ------------------------------------

        if industry == "artificial_intelligence":

            plan.append(

                "technology_analysis"

            )

        # ------------------------------------
        # Remove duplicates
        # ------------------------------------

        final_plan = []

        for engine in plan:

            if engine not in final_plan:

                final_plan.append(engine)

        return {

            "intent": intent,

            "industry": industry,

            "execution_plan": final_plan,

            "engine_count": len(final_plan)

        }


analysis_router = AnalysisRouter()