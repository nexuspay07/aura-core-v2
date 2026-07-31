"""
=========================================================

                    FINDING MODEL

Represents an important observation discovered by
an intelligence engine.

Examples:
- High founder dependency
- Strong market opportunity
- Cash flow risk
- Competitive threat

=========================================================
"""

from pydantic import BaseModel


class Finding(BaseModel):
    """
    Universal intelligence finding.
    """

    title: str

    severity: str
    # very_low
    # low
    # medium
    # high
    # very_high

    description: str

    recommendation: str