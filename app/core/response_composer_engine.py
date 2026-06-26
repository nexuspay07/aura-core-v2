class ResponseComposerEngine:

    """
    Phase 66.5

    Converts all executive intelligence
    into one final Aura response.
    """

    def compose(
        self,
        goal,
        executive_synthesis,
        market_intelligence,
        competitive_intelligence,
        dynamic_reasoning,
        operational_intelligence,
        simulation
    ):

        best_strategy = simulation.get(
            "best_strategy",
            {}
        )

        return {

            "executive_summary":
                executive_synthesis.get(
                    "executive_recommendation",
                    ""
                ),

            "market_view": {

                "market_type":
                    market_intelligence.get(
                        "market_type"
                    ),

                "growth_rate":
                    market_intelligence.get(
                        "growth_rate"
                    ),

                "competition":
                    market_intelligence.get(
                        "competition_level"
                    )
            },

            "competitive_view": {

                "advantage":
                    competitive_intelligence.get(
                        "competitive_advantage"
                    ),

                "moat":
                    competitive_intelligence.get(
                        "recommended_moat"
                    ),

                "risk":
                    competitive_intelligence.get(
                        "competitive_risk"
                    )
            },

            "current_business_reality": {

                "bottleneck":
                    dynamic_reasoning.get(
                        "current_bottleneck"
                    ),

                "priority":
                    dynamic_reasoning.get(
                        "current_priority"
                    ),

                "warning":
                    dynamic_reasoning.get(
                        "strategic_warning"
                    )
            },

            "operational_view": {

                "stability":
                    operational_intelligence.get(
                        "operational_stability"
                    ),

                "scale_readiness":
                    operational_intelligence.get(
                        "scale_readiness"
                    ),

                "main_bottleneck":
                    operational_intelligence.get(
                        "main_operational_bottleneck"
                    )
            },

            "recommended_strategy":
                best_strategy,

            "next_actions":
                executive_synthesis.get(
                    "next_actions",
                    []
                ),

            "confidence":
                executive_synthesis.get(
                    "confidence",
                    50
                )
        }


response_composer_engine = (
    ResponseComposerEngine()
)