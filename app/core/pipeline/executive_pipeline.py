"""
=========================================================

                EXECUTIVE PIPELINE

Executes Aura Executive Intelligence.

Pipeline

AuraRequest
    ↓
Strategic Analysis
    ↓
Market Intelligence
    ↓
Competitive Intelligence
    ↓
Business Understanding
    ↓
Dynamic Reasoning
    ↓
Executive Summary
    ↓
request.executive

=========================================================
"""

from app.core.executive_intelligence.strategic_analysis_engine import (
    strategic_analysis_engine,
)

from app.core.executive_intelligence.market_intelligence_engine import (
    market_intelligence_engine,
)

from app.core.executive_intelligence.competitive_intelligence_engine import (
    competitive_intelligence_engine,
)

from app.core.business_understanding_engine import (
    business_understanding_engine,
)

from app.core.reasoning.dynamic_reasoning_engine import (
    dynamic_reasoning_engine,
)


class ExecutivePipeline:

    # =====================================================
    # BUILD EXECUTIVE SUMMARY
    # =====================================================

    def _build_executive_analysis(
        self,
        strategic_analysis,
        market_intelligence,
        competitive_intelligence,
        business_understanding,
        dynamic_reasoning,
    ):

        business_dna = business_understanding.get(
            "business_dna",
            {},
        )

        confidence = strategic_analysis.get(
            "confidence_score",
            0.60,
        )

        return {

            "summary":
                "Executive analysis completed successfully.",

            "confidence":
                round(confidence * 100, 2),

            "business_stage":
                business_dna.get(
                    "business_stage",
                    "unknown",
                ),

            "business_model":
                business_dna.get(
                    "business_model",
                    "unknown",
                ),

            "recommended_focus":
                dynamic_reasoning.get(
                    "current_priority",
                    "General business improvement",
                ),

            "primary_risk":
                dynamic_reasoning.get(
                    "strategic_warning",
                    "No major strategic warning.",
                ),

            "primary_opportunity":
                market_intelligence.get(
                    "recommended_positioning",
                    "Continue validating opportunities.",
                ),

            "market_growth":
                market_intelligence.get(
                    "growth_rate",
                    "unknown",
                ),

            "competition":
                market_intelligence.get(
                    "competition_level",
                    "unknown",
                ),
        }

    # =====================================================
    # RUN PIPELINE
    # =====================================================

    def run(self, request):

        goal = request.goal
        profile = request.profile or {}
        scenario = request.scenario or {}

        #
        # Keep old engines compatible while moving
        # toward AuraRequest as the single source
        #

        if request.business_context:
            scenario["business_context"] = request.business_context

        if request.unified_context:
            scenario["unified_context"] = request.unified_context

        # =====================================
        # Strategic Analysis
        # =====================================

        strategic_analysis = strategic_analysis_engine.analyze(
            goal,
            profile,
        )

        # =====================================
        # Market Intelligence
        # =====================================

        market_intelligence = market_intelligence_engine.analyze(
            goal=goal,
            strategic_analysis=strategic_analysis,
        )

        # =====================================
        # Competitive Intelligence
        # =====================================

        competitive_intelligence = (
            competitive_intelligence_engine.analyze(
                strategic_analysis,
                market_intelligence,
            )
        )

        # =====================================
        # Business Understanding
        # =====================================

        business_understanding = (
            business_understanding_engine.analyze(
                goal=goal,
                scenario=scenario,
                strategic_analysis=strategic_analysis,
                market_intelligence=market_intelligence,
                competitive_intelligence=competitive_intelligence,
            )
        )

        # =====================================
        # Business DNA
        # =====================================

        business_dna = business_understanding.get(
            "business_dna",
            {},
        )

        # =====================================
        # Dynamic Reasoning
        # =====================================

        dynamic_reasoning = dynamic_reasoning_engine.analyze(
            business_dna,
        )

        # =====================================
        # Executive Summary
        # =====================================

        executive_analysis = self._build_executive_analysis(
            strategic_analysis,
            market_intelligence,
            competitive_intelligence,
            business_understanding,
            dynamic_reasoning,
        )

       # ==================================================
# Save Into AuraRequest
# ==================================================

        request.executive.strategic_analysis = strategic_analysis

        request.executive.market_intelligence = market_intelligence

        request.executive.competitive_intelligence = (
              competitive_intelligence
        )

        request.executive.business_understanding = (
           business_understanding
        )

        request.executive.dynamic_reasoning = (
            dynamic_reasoning
        )

        request.executive.executive_analysis = (
            executive_analysis
        )

        return request


executive_pipeline = ExecutivePipeline()