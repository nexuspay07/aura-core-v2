"""
=========================================================

                ENGINE RESULT

Universal output model for every AURA engine.

Every intelligence engine should return an
EngineResult instead of arbitrary dictionaries.

=========================================================
"""

from typing import Any

from pydantic import BaseModel, Field

from app.core.models.metrics import Metric
from app.core.models.finding import Finding


class EngineResult(BaseModel):
    """
    Standard result returned by every engine.
    """

    engine: str = Field(
        description="Name of the engine."
    )

    version: str = "2.0"

    status: str = "success"

    metrics: dict[str, Metric] = Field(
        default_factory=dict,
        description="Structured metrics produced by the engine."
    )

    findings: list[Finding] = Field(
        default_factory=list,
        description="Key findings."
    )

    reasoning: list[str] = Field(
        default_factory=list
    )

    recommendations: list[str] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )