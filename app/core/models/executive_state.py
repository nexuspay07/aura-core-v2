"""
=========================================================

                EXECUTIVE STATE

Stores all executive intelligence produced during
the Executive Pipeline.

=========================================================
"""

from pydantic import BaseModel, Field


class ExecutiveState(BaseModel):
    """
    Executive Pipeline State
    """

    strategic_analysis: dict = Field(default_factory=dict)

    market_intelligence: dict = Field(default_factory=dict)

    competitive_intelligence: dict = Field(default_factory=dict)

    business_understanding: dict = Field(default_factory=dict)

    dynamic_reasoning: dict = Field(default_factory=dict)

    executive_analysis: dict = Field(default_factory=dict)

    metadata: dict = Field(default_factory=dict)