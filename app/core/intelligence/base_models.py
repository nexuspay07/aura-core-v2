"""
=========================================================

        AURA INTELLIGENCE BASE MODELS

Every intelligence object inherits from these models.

=========================================================
"""

from typing import Optional
from pydantic import BaseModel, Field


class IntelligenceMetric(BaseModel):
    """
    Standard intelligence metric.

    value:
        Raw score (0-100)

    level:
        very_low / low / medium / high / very_high

    confidence:
        Confidence in this metric (0-1)
    """

    value: float = Field(
        ge=0,
        le=100
    )

    level: str

    confidence: float = Field(
        ge=0,
        le=1
    )

    explanation: Optional[str] = None


class IntelligenceResult(BaseModel):
    """
    Parent for every engine result.
    """

    status: str = "success"

    version: str = "2.0"

    reasoning: list[str] = []

    warnings: list[str] = []