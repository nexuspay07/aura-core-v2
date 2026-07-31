"""
=========================================================

                SIMULATION STATE

Stores all intelligence produced during the
Simulation Pipeline.

Every Simulation Pipeline engine writes its output
here.

=========================================================
"""

from pydantic import BaseModel, Field


class SimulationState(BaseModel):
    """
    Simulation Pipeline State
    """

    simulation: dict = Field(default_factory=dict)

    world_model: dict = Field(default_factory=dict)

    prediction: dict = Field(default_factory=dict)

    strategic_simulation: dict = Field(default_factory=dict)

    deep_reasoning: dict = Field(default_factory=dict)

    operational_intelligence: dict = Field(default_factory=dict)

    failure_analysis: dict = Field(default_factory=dict)

    strategy_debate: dict = Field(default_factory=dict)

    visual_intelligence: dict = Field(default_factory=dict)

    metadata: dict = Field(default_factory=dict)