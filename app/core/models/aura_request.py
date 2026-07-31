"""
=========================================================

                    AURA REQUEST

The AuraRequest object is the single source of truth
throughout Aura's cognitive pipeline.

Every service and pipeline enriches the same request
instead of creating new dictionaries.

Flow

User
 ↓
ChatService
 ↓
CognitiveLoop
 ↓
Memory
 ↓
Knowledge
 ↓
Reasoning
 ↓
Planning
 ↓
Execution
 ↓
Executive
 ↓
Simulation
 ↓
Response

=========================================================
"""

from dataclasses import dataclass, field
from typing import Any

from app.core.models.executive_state import (
    ExecutiveState,
)

from app.core.models.simulation_state import (
    SimulationState,
)

from app.core.models.response_state import (
    ResponseState,
)


@dataclass
class AuraRequest:

    # ==========================================
    # CORE REQUEST
    # ==========================================

    goal: str

    profile: dict = field(default_factory=dict)

    scenario: dict = field(default_factory=dict)

    # ==========================================
    # IDENTIFIERS
    # ==========================================

    organization_id: int | None = None

    workspace_id: int | None = None

    # ==========================================
    # CONTEXT
    # ==========================================

    unified_context: dict = field(default_factory=dict)

    business_context: dict = field(default_factory=dict)

    # ==========================================
    # COGNITIVE SERVICES
    # ==========================================

    memory: list[dict] = field(default_factory=list)

    knowledge: dict = field(default_factory=dict)

    reasoning: dict = field(default_factory=dict)

    planning: dict = field(default_factory=dict)

    execution: dict = field(default_factory=dict)

    # ==========================================
# PIPELINES
# ==========================================

    executive: ExecutiveState = field(
    default_factory=ExecutiveState
)

    simulation: SimulationState = field(
    default_factory=SimulationState
)

    response: ResponseState = field(
    default_factory=ResponseState
)
    # ==========================================
    # METADATA
    # ==========================================

    metadata: dict = field(default_factory=dict)

    # ==========================================
    # HELPERS
    # ==========================================

    def update(self, **kwargs):

        """
        Update multiple fields at once.
        """

        for key, value in kwargs.items():

            setattr(self, key, value)

        return self

    def to_dict(self) -> dict[str, Any]:

        """
        Convert to a standard dictionary.
        """

        return self.__dict__

    @property
    def context(self):

        """
        Combined context object.
        """

        return {

            "business": self.business_context,

            "unified": self.unified_context

        }