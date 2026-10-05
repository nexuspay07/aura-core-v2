"""Canonical, provider-neutral Simulation Intelligence contracts."""

from app.simulation.contracts import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationFinding,
    SimulationInputV1,
    SimulationLimitation,
    SimulationResultV1,
    SimulationScenario,
    SimulationType,
    StrategyStressResult,
    UserSimulationAssumption,
)
from app.simulation.serialization import simulation_to_dict, simulation_to_json
from app.simulation.validation import (
    SimulationValidationError,
    validate_simulation_input,
    validate_simulation_result,
)

__all__ = [
    "FindingProvenance",
    "ScenarioSeverity",
    "ScenarioSource",
    "SimulationFinding",
    "SimulationInputV1",
    "SimulationLimitation",
    "SimulationResultV1",
    "SimulationScenario",
    "SimulationType",
    "SimulationValidationError",
    "StrategyStressResult",
    "UserSimulationAssumption",
    "simulation_to_dict",
    "simulation_to_json",
    "validate_simulation_input",
    "validate_simulation_result",
]
