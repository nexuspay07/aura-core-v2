"""Provider- and persistence-neutral contracts for Strategy Intelligence.

These objects represent strategic intent only. They deliberately contain no
simulation, execution, outcome, learning, or publication state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.intelligence_v2.contracts import DecisionType


class ConfidenceLevel(str, Enum):
    """Existing Aevric recommendation-confidence labels, not probabilities."""

    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


@dataclass(frozen=True)
class StrategyScope:
    """Already-authorized tenant scope; this object grants no permissions."""

    user_id: int
    organization_id: int | None = None
    workspace_id: int | None = None


@dataclass(frozen=True)
class EvidenceReference:
    """Reference to authorized evidence without copying its private content."""

    evidence_id: str
    citation_label: str | None = None


@dataclass(frozen=True)
class StrategyConstraint:
    """A stable constraint identity and its human-readable meaning."""

    constraint_id: str
    statement: str


@dataclass(frozen=True)
class StrategyAssumption:
    statement: str
    source: str


@dataclass(frozen=True)
class StrategyResource:
    name: str
    description: str


@dataclass(frozen=True)
class StrategyAlternative:
    """An unscored alternative strategic approach."""

    name: str
    approach: str


@dataclass(frozen=True)
class StrategyPhase:
    """An ordered strategic stage, not an executable task."""

    order: int
    name: str
    purpose: str
    focus_areas: tuple[str, ...] = field(default_factory=tuple)
    milestone_intent: str | None = None


@dataclass(frozen=True)
class StrategyRisk:
    """A material risk; mitigation is optional when none is yet grounded."""

    risk: str
    mitigation: str | None = None


@dataclass(frozen=True)
class SuccessMeasure:
    """A measurable or observable condition, without requiring a number."""

    condition: str
    evidence_ref: str | None = None


@dataclass(frozen=True)
class StrategyInput:
    scope: StrategyScope
    objective: str
    chosen_direction: str
    decision_type: DecisionType | None = None
    source_decision_id: int | None = None
    source_reference: str | None = None
    considered_alternatives: tuple[StrategyAlternative, ...] = field(default_factory=tuple)
    constraints: tuple[StrategyConstraint, ...] = field(default_factory=tuple)
    resources: tuple[StrategyResource, ...] = field(default_factory=tuple)
    evidence_refs: tuple[EvidenceReference, ...] = field(default_factory=tuple)
    assumptions: tuple[StrategyAssumption, ...] = field(default_factory=tuple)
    risks: tuple[StrategyRisk, ...] = field(default_factory=tuple)
    uncertainties: tuple[str, ...] = field(default_factory=tuple)
    time_horizon: str | None = None
    change_conditions: tuple[str, ...] = field(default_factory=tuple)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_rationale: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StrategyResult:
    scope: StrategyScope
    objective: str
    chosen_direction: str
    approach: str
    phases: tuple[StrategyPhase, ...]
    success_measures: tuple[SuccessMeasure, ...]
    change_conditions: tuple[str, ...]
    confidence: ConfidenceLevel
    confidence_rationale: tuple[str, ...]
    strategy_id: str | None = None
    source_decision_id: int | None = None
    source_reference: str | None = None
    constraints: tuple[StrategyConstraint, ...] = field(default_factory=tuple)
    assumptions: tuple[StrategyAssumption, ...] = field(default_factory=tuple)
    resources: tuple[StrategyResource, ...] = field(default_factory=tuple)
    risks: tuple[StrategyRisk, ...] = field(default_factory=tuple)
    alternatives: tuple[StrategyAlternative, ...] = field(default_factory=tuple)
    uncertainties: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[EvidenceReference, ...] = field(default_factory=tuple)
    time_horizon: str | None = None
    version: int | None = None
