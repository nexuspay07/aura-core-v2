"""
=========================================================

                RESPONSE PIPELINE

Responsible for generating Aura's final
executive response.

Pipeline

AuraRequest
      ↓
Executive Synthesis
      ↓
Executive Advisor
      ↓
Executive Response
      ↓
Conversation Intelligence
      ↓
Chat Response
      ↓
Response Composer
      ↓
Output Standardization
      ↓
request.response

=========================================================
"""

from app.core.executive_response_engine import (
    executive_response_engine
)

from app.core.executive_synthesis_engine import (
    executive_synthesis_engine
)

from app.core.response_composer_engine import (
    response_composer_engine
)

from app.core.executive_advisor_engine import (
    executive_advisor_engine
)

from app.core.conversational_intelligence_engine import (
    conversational_intelligence_engine
)

from app.core.chat_response_engine import (
    chat_response_engine
)

from app.core.output_standardization_engine import (
    output_standardization_engine
)


class ResponsePipeline:

    """
    Final response generation pipeline.

    This is the final stage before Aura sends a response
    back to the frontend.
    """

    def run(self, request):

        executive = request.executive

        simulation = request.simulation

        # ==================================================
        # Executive Synthesis
        # ==================================================

        synthesis = executive_synthesis_engine.synthesize(
            goal=request.goal,
            strategic_analysis=executive.strategic_analysis,
            market_intelligence=executive.market_intelligence,
            competitive_intelligence=executive.competitive_intelligence,
            business_understanding=executive.business_understanding,
            dynamic_reasoning=executive.dynamic_reasoning,
            prediction=simulation.prediction,
            strategic_simulation=simulation.strategic_simulation,
            operational_intelligence=simulation.operational_intelligence,
            strategy_reinforcement={},
            deep_reasoning=simulation.deep_reasoning,
        )

        # ==================================================
        # Executive Advisor
        # ==================================================

        advisor = executive_advisor_engine.advise(
            goal=request.goal,
            executive_synthesis=synthesis,
            business_understanding=executive.business_understanding,
            dynamic_reasoning=executive.dynamic_reasoning,
            market_intelligence=executive.market_intelligence,
            strategic_simulation=simulation.strategic_simulation,
            operational_intelligence=simulation.operational_intelligence,
        )

        # ==================================================
        # Executive Response
        # ==================================================

        executive_response = (
            executive_response_engine.generate(
                goal=request.goal,
                strategic_analysis=executive.strategic_analysis,
                market_intelligence=executive.market_intelligence,
                competitive_intelligence=executive.competitive_intelligence,
                business_understanding=executive.business_understanding,
                dynamic_reasoning=executive.dynamic_reasoning,
                deep_reasoning=simulation.deep_reasoning,
                prediction=simulation.prediction,
                operational_intelligence=simulation.operational_intelligence,
                best_strategy=simulation.simulation.get("best_strategy", {}),
            )
        )

        # ==================================================
        # Conversational Intelligence
        # ==================================================

        standardized = output_standardization_engine.standardize(
            executive_response=executive_response,
            strategic_simulation=simulation.strategic_simulation,
            operational_intelligence=simulation.operational_intelligence,
            dynamic_reasoning=executive.dynamic_reasoning,
        )

        conversation = conversational_intelligence_engine.generate(
            goal=request.goal,
            executive_advisor=advisor,
            standardized_output=standardized,
            executive_synthesis=synthesis,
        )

        # ==================================================
        # Chat Response
        # ==================================================

        chat = chat_response_engine.generate(
            goal=request.goal,
            conversational_response=conversation,
            executive_advisor=advisor,
            standardized_output=standardized,
        )

        # ==================================================
        # Compose Final Response
        # ==================================================

        composed = response_composer_engine.compose(
            goal=request.goal,
            executive_synthesis=synthesis,
            market_intelligence=executive.market_intelligence,
            competitive_intelligence=executive.competitive_intelligence,
            dynamic_reasoning=executive.dynamic_reasoning,
            operational_intelligence=simulation.operational_intelligence,
            simulation=simulation.simulation,
        )

        # ==================================================
        # Standardize Output
        # ==================================================

        # ==================================================
        # Save Into AuraRequest
        # ==================================================

        request.response.synthesis = synthesis

        request.response.advisor = advisor

        request.response.executive_response = (
    executive_response
)

        request.response.conversation = (
    conversation
)

        request.response.chat = chat

        request.response.composed = composed

        request.response.standardized = (
    standardized
)

       

        return request


response_pipeline = ResponsePipeline()
