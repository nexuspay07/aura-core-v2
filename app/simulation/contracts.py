"""Canonical contracts for Simulation Intelligence V1.

V1 is qualitative Strategy stress testing, not calibrated forecasting. These
contracts deliberately contain no tenant authority, persistence identity,
provider configuration, numerical probability, execution, outcome, or
learning state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyRisk,
    SuccessMeasure,
)


SIMULATION_SCHEMA_VERSION = 1


class SimulationType(str, Enum):
    STRATEGY_STRESS_TEST = "strategy_stress_test"


class ScenarioSource(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class ScenarioSeverity(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class FindingProvenance(str, Enum):
    SOURCE = "SOURCE"
    USER_SUPPLIED = "USER_SUPPLIED"
    MODEL_GENERATED = "MODEL_GENERATED"
    DERIVED = "DERIVED"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class SimulationScenario:
    key: str
    name: str
    description: str
    changed_conditions: tuple[str, ...]
    source: ScenarioSource
    severity: ScenarioSeverity | None = None


@dataclass(frozen=True)
class UserSimulationAssumption:
    statement: str
    scenario_key: str | None = None
    provenance: FindingProvenance = FindingProvenance.USER_SUPPLIED


@dataclass(frozen=True)
class SimulationInputV1:
    """Immutable Strategy material and explicit scenarios for one stress test."""

    objective: str
    chosen_direction: str
    strategic_approach: str
    phases: tuple[StrategyPhase, ...]
    success_measures: tuple[SuccessMeasure, ...]
    scenarios: tuple[SimulationScenario, ...]
    constraints: tuple[StrategyConstraint, ...] = field(default_factory=tuple)
    resources: tuple[StrategyResource, ...] = field(default_factory=tuple)
    risks: tuple[StrategyRisk, ...] = field(default_factory=tuple)
    strategy_assumptions: tuple[StrategyAssumption, ...] = field(default_factory=tuple)
    uncertainties: tuple[str, ...] = field(default_factory=tuple)
    change_conditions: tuple[str, ...] = field(default_factory=tuple)
    time_horizon: str | None = None
    evidence_refs: tuple[EvidenceReference, ...] = field(default_factory=tuple)
    user_assumptions: tuple[UserSimulationAssumption, ...] = field(default_factory=tuple)
    simulation_type: SimulationType = SimulationType.STRATEGY_STRESS_TEST
    schema_version: int = SIMULATION_SCHEMA_VERSION


@dataclass(frozen=True)
class SimulationFinding:
    statement: str
    provenance: FindingProvenance
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SimulationLimitation:
    code: str
    statement: str
    provenance: FindingProvenance = FindingProvenance.SYSTEM


@dataclass(frozen=True)
class StrategyStressResult:
    scenario_key: str
    elements_under_stress: tuple[SimulationFinding, ...]
    plausible_effects: tuple[SimulationFinding, ...]
    sensitivity: ScenarioSeverity
    constraint_conflicts: tuple[SimulationFinding, ...] = field(default_factory=tuple)
    risk_observations: tuple[SimulationFinding, ...] = field(default_factory=tuple)
    mitigation_observations: tuple[SimulationFinding, ...] = field(default_factory=tuple)
    phase_sensitivities: tuple[SimulationFinding, ...] = field(default_factory=tuple)
    upside_conditions: tuple[SimulationFinding, ...] = field(default_factory=tuple)
    downside_conditions: tuple[SimulationFinding, ...] = field(default_factory=tuple)
    change_condition_triggers: tuple[SimulationFinding, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SimulationResultV1:
    scenario_results: tuple[StrategyStressResult, ...]
    cross_scenario_comparison: tuple[SimulationFinding, ...]
    assumptions_used: tuple[SimulationFinding, ...]
    uncertainties: tuple[SimulationFinding, ...]
    limitations: tuple[SimulationLimitation, ...]
    confidence: ConfidenceLevel
    confidence_rationale: tuple[str, ...]
    evidence_refs: tuple[EvidenceReference, ...] = field(default_factory=tuple)
    simulation_type: SimulationType = SimulationType.STRATEGY_STRESS_TEST
    schema_version: int = SIMULATION_SCHEMA_VERSION
