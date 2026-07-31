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


class CognitiveLoop:

    """
    Top-level orchestration for Aura.

    The Cognitive Loop performs no intelligence itself.

    Every pipeline enriches the same AuraRequest.
    """

    def __init__(self):

        print("[COGNITIVE LOOP V2] Initialized")

    # ======================================================
    # RUN
    # ======================================================

    async def run(
        self,
        request: AuraRequest,
    ) -> AuraRequest:

        print("\n========== AURA REQUEST ==========")
        print(request)
        print("==================================\n")

        # ==================================================
        # Executive Pipeline
        # ==================================================

        print("\n========== EXECUTIVE PIPELINE ==========")

        request = executive_pipeline.run(
            request
        )

        print("Executive Pipeline Complete.")

        # ==================================================
        # Simulation Pipeline
        # ==================================================

        print("\n========== SIMULATION PIPELINE ==========")

        request = simulation_pipeline.run(
            request
        )

        print("Simulation Pipeline Complete.")

        # ==================================================
        # Response Pipeline
        # ==================================================

        print("\n========== RESPONSE PIPELINE ==========")

        request = response_pipeline.run(
            request
        )

        print("Response Pipeline Complete.")

        return request


cognitive_loop = CognitiveLoop()