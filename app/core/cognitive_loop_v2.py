"""
=========================================================

                AURA COGNITIVE LOOP V2

Top-level orchestrator for Aura.

Responsibilities

• Execute Executive Pipeline
• Execute Simulation Pipeline
• Execute Response Pipeline
• Return the enriched AuraRequest

=========================================================
"""

import logging

from app.core.models.aura_request import AuraRequest

from app.core.pipeline.executive_pipeline import (
    executive_pipeline,
)

from app.core.pipeline.simulation_pipeline import (
    simulation_pipeline,
)

from app.core.pipeline.response_pipeline import (
    response_pipeline,
)


logger = logging.getLogger(__name__)


class CognitiveLoop:

    """
    Top-level orchestration for Aura.

    The Cognitive Loop performs no intelligence itself.

    Every pipeline enriches the same AuraRequest.
    """

    def __init__(self):

        logger.info("Cognitive loop initialized")

    # ======================================================
    # RUN
    # ======================================================

    async def run(
        self,
        request: AuraRequest,
    ) -> AuraRequest:

        # ==================================================
        # Executive Pipeline
        # ==================================================

        request = executive_pipeline.run(
            request
        )

        logger.debug("Executive pipeline completed")

        # ==================================================
        # Simulation Pipeline
        # ==================================================

        request = simulation_pipeline.run(
            request
        )

        logger.debug("Simulation pipeline completed")

        # ==================================================
        # Response Pipeline
        # ==================================================

        request = response_pipeline.run(
            request
        )

        logger.debug("Response pipeline completed")

        return request


cognitive_loop = CognitiveLoop()
