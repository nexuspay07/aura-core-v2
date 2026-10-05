"""Pure adapters into canonical Simulation Intelligence contracts."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from app.simulation.contracts import (
    SimulationExecutionInputV1,
    SimulationInputV1,
    SimulationScenario,
    SimulationSourceProvenanceV1,
    UserSimulationAssumption,
)
from app.simulation.validation import validate_simulation_execution_input
from app.strategy.contracts import StrategyResult
from app.strategy.validation import StrategyValidationError, validate_strategy_result


class SimulationAdapterError(ValueError):
    """Trusted source material is insufficient for a Simulation execution."""


def _snapshot(values: Iterable[object]) -> tuple:
    return tuple(item for item in values)


def build_simulation_input_from_strategy_revision(
    strategy_revision: StrategyResult,
    *,
    strategy_schema_version: int,
    scenarios: Iterable[SimulationScenario],
    user_assumptions: Iterable[UserSimulationAssumption] = (),
) -> SimulationExecutionInputV1:
    """Map one already-selected, hydrated Strategy revision without inference.

    The caller selects and authorizes the exact revision. Internal Strategy,
    revision, Decision snapshot, and tenant IDs never cross this boundary.
    """

    try:
        validate_strategy_result(strategy_revision)
    except StrategyValidationError as error:
        raise SimulationAdapterError("strategy_revision is not valid canonical Strategy material") from error

    public_id = strategy_revision.strategy_id
    if not isinstance(public_id, str):
        raise SimulationAdapterError("strategy_revision.strategy_id must be a public UUID")
    try:
        UUID(public_id)
    except (ValueError, AttributeError) as error:
        raise SimulationAdapterError(
            "strategy_revision.strategy_id must be a public UUID"
        ) from error

    revision = strategy_revision.version
    if not isinstance(revision, int) or isinstance(revision, bool) or revision <= 0:
        raise SimulationAdapterError("strategy_revision.version must pin an exact positive revision")
    if (
        not isinstance(strategy_schema_version, int)
        or isinstance(strategy_schema_version, bool)
        or strategy_schema_version <= 0
    ):
        raise SimulationAdapterError("strategy_schema_version must be a positive integer")

    analytical_input = SimulationInputV1(
        objective=strategy_revision.objective,
        chosen_direction=strategy_revision.chosen_direction,
        strategic_approach=strategy_revision.approach,
        phases=_snapshot(strategy_revision.phases),
        success_measures=_snapshot(strategy_revision.success_measures),
        scenarios=_snapshot(scenarios),
        constraints=_snapshot(strategy_revision.constraints),
        resources=_snapshot(strategy_revision.resources),
        risks=_snapshot(strategy_revision.risks),
        strategy_assumptions=_snapshot(strategy_revision.assumptions),
        uncertainties=_snapshot(strategy_revision.uncertainties),
        change_conditions=_snapshot(strategy_revision.change_conditions),
        time_horizon=strategy_revision.time_horizon,
        evidence_refs=_snapshot(strategy_revision.evidence_refs),
        user_assumptions=_snapshot(user_assumptions),
    )
    execution_input = SimulationExecutionInputV1(
        provenance=SimulationSourceProvenanceV1(
            strategy_public_id=public_id,
            strategy_revision=revision,
            strategy_schema_version=strategy_schema_version,
        ),
        simulation_input=analytical_input,
    )
    validate_simulation_execution_input(execution_input)
    return execution_input
