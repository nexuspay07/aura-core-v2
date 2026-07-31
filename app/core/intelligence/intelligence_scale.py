"""
=========================================================

            AURA INTELLIGENCE SCALE

Centralised scoring system used by every engine.

No engine should hard-code values such as
50, 60, 75 or 80.

=========================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntelligenceThresholds:

    VERY_LOW = 20
    LOW = 40
    MEDIUM = 60
    HIGH = 80
    VERY_HIGH = 100


class IntelligenceScale:

    @staticmethod
    def level(score: float | int | None) -> str:

        if score is None:
            return "unknown"

        if score <= IntelligenceThresholds.VERY_LOW:
            return "very_low"

        if score <= IntelligenceThresholds.LOW:
            return "low"

        if score <= IntelligenceThresholds.MEDIUM:
            return "medium"

        if score <= IntelligenceThresholds.HIGH:
            return "high"

        return "very_high"

    @staticmethod
    def is_high(score):

        return IntelligenceScale.level(score) in (
            "high",
            "very_high",
        )

    @staticmethod
    def is_medium_or_higher(score):

        return IntelligenceScale.level(score) in (
            "medium",
            "high",
            "very_high",
        )

    @staticmethod
    def is_low(score):

        return IntelligenceScale.level(score) in (
            "low",
            "very_low",
        )


intelligence_scale = IntelligenceScale()