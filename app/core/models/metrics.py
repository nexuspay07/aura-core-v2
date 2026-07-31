"""
=========================================================

                    METRIC MODEL

Represents one measurable intelligence value.

Every engine should use Metric instead of raw
numbers wherever possible.

=========================================================
"""

from pydantic import BaseModel, Field


class Metric(BaseModel):
    """
    Universal intelligence metric.
    """

    name: str

    value: float = Field(
        ge=0,
        le=100,
        description="Metric value (0-100)."
    )

    level: str = Field(
        description="very_low, low, medium, high, very_high"
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in this metric (0-1)."
    )

    explanation: str = ""