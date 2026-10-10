"""Authenticated HTTP presentation boundary for canonical Simulation V1."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.database import SessionLocal
from app.simulation.application import (
    CreateStrategyStressTestCommand,
    SimulationApplicationConflictError,
    SimulationApplicationGenerationError,
    SimulationApplicationInProgressError,
    SimulationApplicationInternalError,
    SimulationApplicationNotFoundError,
    SimulationApplicationPersistenceError,
    SimulationApplicationValidationError,
    StrategyStressTestApplicationResult,
    simulation_application_service,
)
from app.simulation.contracts import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationResultV1,
    SimulationScenario,
    SimulationType,
    UserSimulationAssumption,
)
from app.simulation.persistence import (
    PersistedSimulationResource,
    SimulationPersistenceError,
    SimulationPersistenceNotFoundError,
    simulation_repository,
)
from app.simulation.serialization import simulation_to_dict
from app.strategy.contracts import ConfidenceLevel
from app.strategy.routes import authorized_scope, current_identity


router = APIRouter(tags=["Simulation Resources"])


class SimulationScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    name: str = Field(min_length=1, max_length=4000)
    description: str = Field(min_length=1, max_length=4000)
    changed_conditions: list[str] = Field(min_length=1, max_length=20)
    qualitative_severity: ScenarioSeverity | None = None


class UserSimulationAssumptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    scenario_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{0,63}$")


class CreateStrategyStressTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="Strategy Stress Test", min_length=1, max_length=255)
    scenarios: list[SimulationScenarioRequest] = Field(min_length=1, max_length=6)
    user_assumptions: list[UserSimulationAssumptionRequest] = Field(default_factory=list, max_length=30)


class EvidenceReferenceResponse(BaseModel):
    evidence_id: str
    citation_label: str | None


class SimulationFindingResponse(BaseModel):
    statement: str
    provenance: FindingProvenance
    evidence_refs: list[str]


class SimulationLimitationResponse(BaseModel):
    code: str
    statement: str
    provenance: FindingProvenance


class StrategyStressScenarioResponse(BaseModel):
    scenario_key: str
    elements_under_stress: list[SimulationFindingResponse]
    plausible_effects: list[SimulationFindingResponse]
    sensitivity: ScenarioSeverity
    constraint_conflicts: list[SimulationFindingResponse]
    risk_observations: list[SimulationFindingResponse]
    mitigation_observations: list[SimulationFindingResponse]
    phase_sensitivities: list[SimulationFindingResponse]
    upside_conditions: list[SimulationFindingResponse]
    downside_conditions: list[SimulationFindingResponse]
    change_condition_triggers: list[SimulationFindingResponse]


class SimulationResultResponse(BaseModel):
    scenario_results: list[StrategyStressScenarioResponse]
    cross_scenario_comparison: list[SimulationFindingResponse]
    assumptions_used: list[SimulationFindingResponse]
    uncertainties: list[SimulationFindingResponse]
    limitations: list[SimulationLimitationResponse]
    confidence: ConfidenceLevel
    confidence_rationale: list[str]
    evidence_refs: list[EvidenceReferenceResponse]
    simulation_type: SimulationType
    schema_version: int


class SimulationResourceSummaryResponse(BaseModel):
    simulation_public_id: str
    simulation_type: SimulationType
    title: str
    source_strategy_public_id: str
    source_strategy_revision: int
    source_decision_snapshot_public_id: str | None
    current_run_number: int
    created_at: datetime
    updated_at: datetime
    archived: bool


class SimulationResourceListResponse(BaseModel):
    items: list[SimulationResourceSummaryResponse]


class SimulationResourceDetailResponse(BaseModel):
    simulation_public_id: str
    simulation_type: SimulationType
    title: str
    source_strategy_public_id: str
    source_strategy_revision: int
    source_decision_snapshot_public_id: str | None
    run_number: int
    result: SimulationResultResponse
    created_at: datetime
    archived: bool


class SimulationErrorDetailResponse(BaseModel):
    code: str
    message: str


class SimulationPublicErrorResponse(BaseModel):
    detail: str | SimulationErrorDetailResponse | list[dict[str, object]]


_COMMON_RESPONSES = {
    401: {"model": SimulationPublicErrorResponse, "description": "Authentication is missing, invalid, or expired."},
    403: {"model": SimulationPublicErrorResponse, "description": "Authentication credentials were not supplied."},
    422: {"model": SimulationPublicErrorResponse, "description": "Request parameters or fields did not pass validation."},
    500: {"model": SimulationPublicErrorResponse, "description": "The operation could not be completed."},
    503: {"model": SimulationPublicErrorResponse, "description": "Simulation persistence is temporarily unavailable."},
}
_CREATE_RESPONSES = {
    **_COMMON_RESPONSES,
    404: {"model": SimulationPublicErrorResponse, "description": "The Strategy is not available in the authenticated scope."},
    409: {"model": SimulationPublicErrorResponse, "description": "The idempotent request is in progress or conflicts with its original request."},
    502: {"model": SimulationPublicErrorResponse, "description": "Generation could not produce a valid canonical result."},
}
_DETAIL_RESPONSES = {
    **_COMMON_RESPONSES,
    404: {"model": SimulationPublicErrorResponse, "description": "The Simulation is not available in the authenticated scope."},
}


def _result(value: SimulationResultV1) -> SimulationResultResponse:
    return SimulationResultResponse.model_validate(simulation_to_dict(value))


def _created(value: StrategyStressTestApplicationResult) -> SimulationResourceDetailResponse:
    return SimulationResourceDetailResponse(
        simulation_public_id=value.simulation_public_id,
        simulation_type=value.simulation_type,
        title=value.title,
        source_strategy_public_id=value.source_strategy_public_id,
        source_strategy_revision=value.source_strategy_revision,
        source_decision_snapshot_public_id=value.source_decision_snapshot_public_id,
        run_number=value.run_number,
        result=_result(value.result),
        created_at=value.created_at,
        archived=value.archived,
    )


def _summary(value: PersistedSimulationResource) -> SimulationResourceSummaryResponse:
    return SimulationResourceSummaryResponse(
        simulation_public_id=value.public_id,
        simulation_type=value.simulation_type,
        title=value.title,
        source_strategy_public_id=value.source_strategy_public_id,
        source_strategy_revision=value.source_strategy_revision,
        source_decision_snapshot_public_id=value.source_decision_snapshot_public_id,
        current_run_number=value.current_run_number,
        created_at=value.created_at,
        updated_at=value.updated_at,
        archived=value.archived_at is not None,
    )


def _detail(db, value: PersistedSimulationResource, scope) -> SimulationResourceDetailResponse:
    run = simulation_repository.get_latest_run(db, resource_public_id=value.public_id, scope=scope)
    return SimulationResourceDetailResponse(
        simulation_public_id=value.public_id,
        simulation_type=value.simulation_type,
        title=value.title,
        source_strategy_public_id=value.source_strategy_public_id,
        source_strategy_revision=value.source_strategy_revision,
        source_decision_snapshot_public_id=value.source_decision_snapshot_public_id,
        run_number=run.run_number,
        result=_result(run.result),
        created_at=value.created_at,
        archived=value.archived_at is not None,
    )


def _application_error(error: Exception) -> None:
    if isinstance(error, SimulationApplicationInProgressError):
        raise HTTPException(status_code=409, detail={"code": "simulation_creation_in_progress", "message": "The same Simulation creation is already in progress."}) from error
    if isinstance(error, SimulationApplicationNotFoundError):
        raise HTTPException(status_code=404, detail="Strategy not found") from error
    if isinstance(error, SimulationApplicationConflictError):
        raise HTTPException(status_code=409, detail={"code": "simulation_conflict", "message": "Simulation request conflicts with current state."}) from error
    if isinstance(error, SimulationApplicationValidationError):
        raise HTTPException(status_code=422, detail="Simulation request did not pass validation.") from error
    if isinstance(error, SimulationApplicationGenerationError):
        raise HTTPException(status_code=502, detail="Simulation generation could not produce a valid response.") from error
    if isinstance(error, SimulationApplicationPersistenceError):
        raise HTTPException(status_code=503, detail="Simulation persistence is temporarily unavailable.") from error
    if isinstance(error, SimulationApplicationInternalError):
        raise HTTPException(status_code=500, detail="Simulation operation could not be completed.") from error
    raise HTTPException(status_code=500, detail="Simulation operation could not be completed.") from error


def _request(body: CreateStrategyStressTestRequest, strategy_public_id: UUID, key: str):
    if not key.strip():
        raise HTTPException(status_code=422, detail="Idempotency-Key must be meaningful.")
    return CreateStrategyStressTestCommand(
        strategy_public_id=str(strategy_public_id), title=body.title,
        idempotency_key=key.strip(),
        scenarios=tuple(SimulationScenario(
            item.key, item.name, item.description, tuple(item.changed_conditions),
            ScenarioSource.USER_SUPPLIED, item.qualitative_severity,
        ) for item in body.scenarios),
        user_assumptions=tuple(UserSimulationAssumption(
            item.text, item.scenario_key, FindingProvenance.USER_SUPPLIED,
        ) for item in body.user_assumptions),
    )


@router.post(
    "/strategy-resources/{strategy_public_id}/simulations",
    response_model=SimulationResourceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Strategy Stress Test",
    description="Run canonical qualitative scenario analysis for an authorized persisted Strategy. Requires Idempotency-Key.",
    responses=_CREATE_RESPONSES,
)
async def create_strategy_stress_test(
    strategy_public_id: UUID,
    body: CreateStrategyStressTestRequest,
    idempotency_key: str = Header(min_length=1, max_length=255, alias="Idempotency-Key", description="Required retry-safe creation key."),
    identity=Depends(current_identity),
) -> SimulationResourceDetailResponse:
    scope = authorized_scope(identity)
    command = _request(body, strategy_public_id, idempotency_key)
    db = SessionLocal()
    try:
        return _created(simulation_application_service.create_strategy_stress_test(
            db, command=command, actor_user_id=scope.user_id, scope=scope,
        ))
    except SimulationApplicationErrorTypes as error:
        _application_error(error)
    finally:
        db.close()


SimulationApplicationErrorTypes = (
    SimulationApplicationValidationError,
    SimulationApplicationNotFoundError,
    SimulationApplicationConflictError,
    SimulationApplicationGenerationError,
    SimulationApplicationPersistenceError,
    SimulationApplicationInternalError,
)


@router.get(
    "/simulation-resources",
    response_model=SimulationResourceListResponse,
    summary="List saved Strategy Stress Tests",
    description="List canonical qualitative scenario-analysis resources in the authenticated exact scope.",
    responses=_COMMON_RESPONSES,
)
async def list_simulation_resources(
    limit: int = Query(default=50, ge=1, le=100),
    identity=Depends(current_identity),
) -> SimulationResourceListResponse:
    scope = authorized_scope(identity)
    db = SessionLocal()
    try:
        if scope.organization_id is None:
            values = simulation_repository.list_personal_resources(db, owner_user_id=scope.user_id, limit=limit)
        else:
            values = simulation_repository.list_workspace_resources(db, organization_id=scope.organization_id, workspace_id=scope.workspace_id, limit=limit)
        return SimulationResourceListResponse(items=[_summary(value) for value in values])
    except SimulationPersistenceError as error:
        raise HTTPException(status_code=503, detail="Simulation resources are temporarily unavailable.") from error
    finally:
        db.close()


@router.get(
    "/simulation-resources/{simulation_public_id}",
    response_model=SimulationResourceDetailResponse,
    summary="Get a saved Strategy Stress Test",
    description="Retrieve canonical qualitative scenario-analysis detail from the authenticated exact scope.",
    responses=_DETAIL_RESPONSES,
)
async def get_simulation_resource(
    simulation_public_id: UUID,
    identity=Depends(current_identity),
) -> SimulationResourceDetailResponse:
    scope = authorized_scope(identity)
    db = SessionLocal()
    try:
        if scope.organization_id is None:
            value = simulation_repository.get_personal_resource(db, public_id=str(simulation_public_id), owner_user_id=scope.user_id)
        else:
            value = simulation_repository.get_workspace_resource(
                db, public_id=str(simulation_public_id), organization_id=scope.organization_id, workspace_id=scope.workspace_id,
            )
        return _detail(db, value, scope)
    except SimulationPersistenceNotFoundError as error:
        raise HTTPException(status_code=404, detail="Simulation not found") from error
    except SimulationPersistenceError as error:
        raise HTTPException(status_code=503, detail="Simulation resource is temporarily unavailable.") from error
    finally:
        db.close()
