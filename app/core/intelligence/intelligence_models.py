from dataclasses import dataclass
from typing import Optional


@dataclass
class IntelligenceScore:
    """
    Standard numerical intelligence score.
    """

    value: float
    level: str
    confidence: float


@dataclass
class OpportunityAssessment:

    score: IntelligenceScore
    explanation: str


@dataclass
class ThreatAssessment:

    score: IntelligenceScore
    explanation: str


@dataclass
class RiskAssessment:

    score: IntelligenceScore
    explanation: str


@dataclass
class ConfidenceAssessment:

    score: IntelligenceScore
    explanation: str