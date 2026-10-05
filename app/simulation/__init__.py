"""Canonical, provider-neutral Simulation Intelligence contracts."""

from app.simulation.adapters import (
    SimulationAdapterError,
    build_simulation_input_from_strategy_revision,
)
from app.simulation.contracts import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationFinding,
    SimulationExecutionInputV1,
    SimulationInputV1,
    SimulationLimitation,
    SimulationResultV1,
    SimulationScenario,
    SimulationSourceProvenanceV1,
    SimulationSourceType,
    SimulationType,
    StrategyStressResult,
    UserSimulationAssumption,
)
from app.simulation.quality import (
    NON_FORECAST_LIMITATION_CODE,
    SimulationQualityError,
    SimulationQualityIssue,
    validate_simulation_result_quality,
)
from app.simulation.serialization import simulation_to_dict, simulation_to_json
from app.simulation.validation import (
    SimulationValidationError,
    validate_simulation_execution_input,
    validate_simulation_input,
    validate_simulation_result,
    validate_simulation_source_provenance,
)

__all__ = [
    "FindingProvenance",
    "NON_FORECAST_LIMITATION_CODE",
    "ScenarioSeverity",
    "ScenarioSource",
    "SimulationAdapterError",
    "SimulationExecutionInputV1",
    "SimulationFinding",
    "SimulationInputV1",
    "SimulationLimitation",
    "SimulationQualityError",
    "SimulationQualityIssue",
    "SimulationResultV1",
    "SimulationScenario",
    "SimulationSourceProvenanceV1",
    "SimulationSourceType",
    "SimulationType",
    "SimulationValidationError",
    "StrategyStressResult",
    "UserSimulationAssumption",
    "build_simulation_input_from_strategy_revision",
    "simulation_to_dict",
    "simulation_to_json",
    "validate_simulation_execution_input",
    "validate_simulation_input",
    "validate_simulation_result",
    "validate_simulation_result_quality",
    "validate_simulation_source_provenance",
]
