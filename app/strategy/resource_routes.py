"""Authenticated HTTP boundary for durable Strategy resources."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.database import SessionLocal
from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.strategy.application import (
    StrategyApplicationConflictError,
    StrategyApplicationInProgressError,
    StrategyApplicationNotFoundError,
    StrategyApplicationPersistenceError,
    StrategyApplicationValidationError,
    strategy_application_service,
)
from app.strategy.orchestrator import StrategyGenerationError
from app.strategy.persistence import PersistedStrategy
from app.strategy.presentation import StrategyPresentation, to_strategy_presentation
from app.strategy.quality import StrategyQualityError
from app.strategy.routes import (
    DirectStrategyRequest,
    authorized_scope,
    current_identity,
    to_strategy_input,
)
from app.strategy.validation import StrategyValidationError


router = APIRouter(prefix="/strategy-resources", tags=["Strategy Resources"])


class PersistentStrategyCreateRequest(DirectStrategyRequest):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)


class PersistentStrategyResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_id: str
    title: str
    current_revision: int
    resource_version: int
    archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    strategy: StrategyPresentation


class PersistentStrategyListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_id: str
    title: str
    current_revision: int
    resource_version: int
    archived: bool
    created_at: datetime
    updated_at: datetime


class PersistentStrategyListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PersistentStrategyListItem]


class StrategyArchiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_version: int = Field(gt=0)


def _resource_response(value: PersistedStrategy) -> PersistentStrategyResourceResponse:
    return PersistentStrategyResourceResponse(
        public_id=value.public_id,
        title=value.title,
        current_revision=value.current_revision_number,
        resource_version=value.lock_version,
        archived=value.archived_at is not None,
        archived_at=value.archived_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
        strategy=to_strategy_presentation(value.result),
    )


def _list_item(value: PersistedStrategy) -> PersistentStrategyListItem:
    return PersistentStrategyListItem(
        public_id=value.public_id,
        title=value.title,
        current_revision=value.current_revision_number,
        resource_version=value.lock_version,
        archived=value.archived_at is not None,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _application_error(error: Exception) -> None:
    if isinstance(error, StrategyApplicationInProgressError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "strategy_creation_in_progress",
                "message": "The same Strategy creation is already in progress.",
            },
        ) from error
    if isinstance(error, StrategyApplicationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found") from error
    if isinstance(error, StrategyApplicationConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "strategy_conflict", "message": "Strategy request conflicts with current state."},
        ) from error
    if isinstance(error, StrategyApplicationValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Strategy request did not pass validation.",
        ) from error
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Strategy operation could not be completed.",
    ) from error


def _generation_error(error: Exception) -> None:
    if isinstance(error, ProviderTimeoutError):
        raise HTTPException(status_code=504, detail="Strategy generation timed out. Please try again.") from error
    if isinstance(error, ProviderUnavailableError):
        raise HTTPException(status_code=503, detail="Strategy generation is temporarily unavailable.") from error
    if isinstance(error, InvalidModelResponseError):
        raise HTTPException(status_code=502, detail="Strategy generation could not produce a valid response.") from error
    if isinstance(error, (StrategyQualityError, StrategyValidationError, StrategyGenerationError)):
        raise HTTPException(status_code=422, detail="Strategy input or generated output did not pass validation.") from error
    raise error


@router.post("", response_model=PersistentStrategyResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy_resource(
    body: PersistentStrategyCreateRequest,
    idempotency_key: str = Header(min_length=1, max_length=255, alias="Idempotency-Key"),
    identity=Depends(current_identity),
) -> PersistentStrategyResourceResponse:
    scope = authorized_scope(identity)
    db = SessionLocal()
    try:
        persisted = strategy_application_service.generate_and_persist_idempotent_direct_strategy(
            db,
            strategy_input=to_strategy_input(body, scope),
            title=body.title,
            created_by_user_id=scope.user_id,
            idempotency_key=idempotency_key,
        )
        return _resource_response(persisted)
    except (
        StrategyApplicationValidationError,
        StrategyApplicationPersistenceError,
        StrategyApplicationNotFoundError,
        StrategyApplicationConflictError,
    ) as error:
        _application_error(error)
    except (
        ProviderTimeoutError,
        ProviderUnavailableError,
        InvalidModelResponseError,
        StrategyQualityError,
        StrategyValidationError,
        StrategyGenerationError,
    ) as error:
        _generation_error(error)
    finally:
        db.close()


@router.get("", response_model=PersistentStrategyListResponse)
async def list_strategy_resources(
    limit: int = Query(default=50, ge=1, le=100),
    identity=Depends(current_identity),
) -> PersistentStrategyListResponse:
    scope = authorized_scope(identity)
    db = SessionLocal()
    try:
        if scope.organization_id is None:
            values = strategy_application_service.list_personal_strategies(db, scope=scope, limit=limit)
        else:
            values = strategy_application_service.list_workspace_strategies(db, scope=scope, limit=limit)
        return PersistentStrategyListResponse(items=[_list_item(item) for item in values])
    except (StrategyApplicationValidationError, StrategyApplicationPersistenceError) as error:
        _application_error(error)
    finally:
        db.close()


@router.get("/{strategy_public_id}", response_model=PersistentStrategyResourceResponse)
async def get_strategy_resource(
    strategy_public_id: str,
    identity=Depends(current_identity),
) -> PersistentStrategyResourceResponse:
    scope = authorized_scope(identity)
    db = SessionLocal()
    try:
        if scope.organization_id is None:
            value = strategy_application_service.get_current_personal_strategy(
                db, public_id=strategy_public_id, scope=scope
            )
        else:
            value = strategy_application_service.get_current_workspace_strategy(
                db, public_id=strategy_public_id, scope=scope
            )
        return _resource_response(value)
    except (
        StrategyApplicationValidationError,
        StrategyApplicationPersistenceError,
        StrategyApplicationNotFoundError,
    ) as error:
        _application_error(error)
    finally:
        db.close()


@router.post("/{strategy_public_id}/archive", response_model=PersistentStrategyResourceResponse)
async def archive_strategy_resource(
    strategy_public_id: str,
    body: StrategyArchiveRequest,
    identity=Depends(current_identity),
) -> PersistentStrategyResourceResponse:
    scope = authorized_scope(identity)
    db = SessionLocal()
    try:
        value = strategy_application_service.archive_strategy(
            db,
            public_id=strategy_public_id,
            scope=scope,
            expected_lock_version=body.resource_version,
        )
        db.commit()
        return _resource_response(value)
    except (
        StrategyApplicationValidationError,
        StrategyApplicationPersistenceError,
        StrategyApplicationNotFoundError,
        StrategyApplicationConflictError,
    ) as error:
        db.rollback()
        _application_error(error)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
