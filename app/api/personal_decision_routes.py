from datetime import datetime
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth_routes import get_current_user_from_token
from app.db.database import SessionLocal
from app.db.organization_table import organization_table
from sqlalchemy import select
from app.personal.decisions import (
    DECISION_STATUSES,
    DECISION_TYPES,
    OUTCOME_STATUSES,
    PersonalDecisionError,
    PersonalDecisionAlreadySavedError,
    PersonalDecisionNotFoundError,
    PersonalDecisionTransitionError,
    PersonalDecisionCanonicalSnapshotUnavailableError,
    PersonalDecisionChoiceRequiresReevaluationError,
    personal_decision_service,
)
from app.strategy.adapters import build_strategy_input_from_snapshot
from app.strategy.application import (
    StrategyApplicationConflictError, StrategyApplicationInProgressError,
    StrategyApplicationNotFoundError, StrategyApplicationPersistenceError,
    StrategyApplicationValidationError, strategy_application_service,
)
from app.strategy.contracts import StrategyScope
from app.strategy.resource_routes import PersistentStrategyResourceResponse, _resource_response, _application_error, _generation_error
from app.intelligence_v2.model_provider import InvalidModelResponseError, ProviderTimeoutError, ProviderUnavailableError
from app.strategy.orchestrator import StrategyGenerationError
from app.strategy.quality import StrategyQualityError
from app.strategy.validation import StrategyValidationError


router = APIRouter(prefix="/personal/decisions", tags=["Personal Decisions"])
security = HTTPBearer()
logger = logging.getLogger("uvicorn.error")
_DECISION_STRATEGY_ROUTE = "/personal/decisions/{decision_public_id}/strategy"


def _strategy_http_event(stage: str, *, category: str = "none", status_code: int | None = None, quality_codes: str = "none", generation_codes: str = "none") -> None:
    logger.warning(
        "strategy_http_stage=%s category=%s status_code=%s quality_codes=%s generation_codes=%s",
        stage, category, status_code if status_code is not None else "none", quality_codes, generation_codes,
    )


async def strategy_request_validation_handler(request: Request, error: RequestValidationError):
    route = request.scope.get("route")
    if getattr(route, "path", None) == _DECISION_STRATEGY_ROUTE:
        _strategy_http_event("request_failed", category="fastapi_request_validation", status_code=422)
    return await request_validation_exception_handler(request, error)


class DecisionCreateRequest(BaseModel):
    source_session_id: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    decision_type: str = Field(default="decision_analysis", max_length=64)


class DecisionUpdateRequest(BaseModel):
    user_choice: str | None = Field(default=None, min_length=1, max_length=4000)
    user_choice_rationale: str | None = Field(default=None, max_length=4000)
    decision_date: datetime | None = None
    review_date: datetime | None = None
    status: Literal["open", "decided", "awaiting_outcome", "completed"] | None = None
    outcome_status: Literal["not_recorded", "pending", "recorded"] | None = None

class DecisionStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)


async def current_identity(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await get_current_user_from_token(credentials)


def scope(identity: dict) -> tuple[int, int, int]:
    user = identity.get("user") or {}
    organization = identity.get("organization") or {}
    workspace = identity.get("workspace") or {}
    if "decisions" not in identity.get("capabilities", []):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal decisions are not available")
    if not all(isinstance(item.get("id"), int) for item in (user, organization, workspace)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision workspace not found")
    return user["id"], organization["id"], workspace["id"]


def serialize(record: dict) -> dict:
    result = dict(record)
    result["analysis_snapshot"] = result.pop("analysis_snapshot_json")
    return jsonable_encoder(result)


def failure(error: PersonalDecisionError):
    if isinstance(error, PersonalDecisionAlreadySavedError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, PersonalDecisionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    if isinstance(error, PersonalDecisionTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_decision(body: DecisionCreateRequest, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        result = personal_decision_service.create(db, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id, **body.model_dump())
        db.commit()
        return serialize(result)
    except PersonalDecisionError as error:
        db.rollback()
        failure(error)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("")
async def list_decisions(status_filter: str | None = Query(default=None, alias="status"), decision_type: str | None = None, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    if status_filter is not None and status_filter not in DECISION_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported decision status")
    if decision_type is not None and decision_type not in DECISION_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported decision type")
    db = SessionLocal()
    try:
        return [serialize(record) for record in personal_decision_service.repository.list_owned(db, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id, status=status_filter, decision_type=decision_type)]
    finally:
        db.close()


@router.get("/{decision_id}")
async def get_decision(decision_id: int, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        return serialize(personal_decision_service.repository.get_owned(db, decision_id=decision_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id))
    except PersonalDecisionError as error:
        failure(error)
    finally:
        db.close()


@router.patch("/{decision_id}")
async def update_decision(decision_id: int, body: DecisionUpdateRequest, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        result = personal_decision_service.update(db, decision_id=decision_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id, changes=body.model_dump(exclude_unset=True))
        db.commit()
        return serialize(result)
    except PersonalDecisionError as error:
        db.rollback()
        failure(error)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision(decision_id: int, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        personal_decision_service.delete(db, decision_id=decision_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except PersonalDecisionError as error:
        db.rollback()
        failure(error)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@router.post("/{decision_public_id}/strategy", status_code=status.HTTP_201_CREATED)
async def develop_strategy_from_decision(
    decision_public_id: str,
    body: DecisionStrategyRequest,
    idempotency_key: str = Header(min_length=1, max_length=255, alias="Idempotency-Key"),
    identity=Depends(current_identity),
) -> dict:
    _strategy_http_event("request_entered")
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        decision, snapshot = personal_decision_service.strategy_source(
            db, public_id=decision_public_id, user_id=user_id,
            organization_id=organization_id, workspace_id=workspace_id,
        )
        _strategy_http_event("decision_resolved")
        _strategy_http_event("snapshot_resolved")
        account_type = db.execute(select(organization_table.c.account_type).where(
            organization_table.c.id == organization_id
        )).scalar_one_or_none()
        strategy_scope = (
            StrategyScope(user_id=user_id)
            if account_type == "personal"
            else StrategyScope(user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
        )
        try:
            strategy_input = build_strategy_input_from_snapshot(
                snapshot.snapshot, scope=strategy_scope,
                source_decision_id=decision["id"],
                source_reference=f"personal-decision:{decision['public_id']}",
            )
        except StrategyValidationError as error:
            db.rollback()
            _strategy_http_event("request_failed", category="adapter_validation", status_code=422)
            _generation_error(error)
        _strategy_http_event("adapter_completed")
        _strategy_http_event("input_validation_completed")
        _strategy_http_event("generation_entered")
        persisted = strategy_application_service.generate_and_persist_idempotent_decision_strategy(
            db, strategy_input=strategy_input, title=body.title,
            created_by_user_id=user_id, idempotency_key=idempotency_key,
            personal_decision_public_id=decision["public_id"],
            snapshot_public_id=snapshot.public_id,
            snapshot_version=snapshot.snapshot_version,
            source_decision_snapshot_id=snapshot.id,
        )
        response = _resource_response(persisted).model_dump()
        response["strategy"].pop("source_decision_id", None)
        _strategy_http_event("request_succeeded", status_code=201)
        return jsonable_encoder(response)
    except PersonalDecisionCanonicalSnapshotUnavailableError as error:
        db.rollback()
        _strategy_http_event("request_failed", category="snapshot_validation", status_code=409)
        raise HTTPException(status_code=409, detail={"code":"decision_canonical_snapshot_unavailable","message":"This Decision has no canonical snapshot available."}) from error
    except PersonalDecisionChoiceRequiresReevaluationError as error:
        db.rollback()
        _strategy_http_event("request_failed", category="decision_choice_validation", status_code=409)
        raise HTTPException(status_code=409, detail={"code":"decision_choice_requires_reevaluation","message":"The recorded choice requires Decision re-evaluation before Strategy development."}) from error
    except PersonalDecisionNotFoundError as error:
        db.rollback()
        _strategy_http_event("request_failed", category="decision_not_found", status_code=404)
        raise HTTPException(status_code=404, detail="Decision not found") from error
    except (StrategyApplicationValidationError, StrategyApplicationPersistenceError, StrategyApplicationNotFoundError, StrategyApplicationConflictError) as error:
        db.rollback()
        if isinstance(error, StrategyApplicationValidationError):
            category = "strategy_input_validation" if isinstance(error.__cause__, StrategyValidationError) else "application_validation"
            _strategy_http_event("request_failed", category=category, status_code=422)
        elif isinstance(error, StrategyApplicationPersistenceError):
            _strategy_http_event("persistence_failed", category="persistence", status_code=500)
        elif isinstance(error, StrategyApplicationNotFoundError):
            _strategy_http_event("request_failed", category="application_not_found", status_code=404)
        else:
            _strategy_http_event("request_failed", category="application_conflict", status_code=409)
        _application_error(error)
    except (ProviderTimeoutError, ProviderUnavailableError, InvalidModelResponseError, StrategyQualityError, StrategyValidationError, StrategyGenerationError) as error:
        db.rollback()
        if isinstance(error, StrategyQualityError):
            codes = ",".join(sorted({issue.code for issue in error.issues})) or "none"
            _strategy_http_event("generation_failed", category="strategy_quality_validation", status_code=422, quality_codes=codes)
        elif isinstance(error, StrategyValidationError):
            _strategy_http_event("generation_failed", category="strategy_structural_validation", status_code=422)
        elif isinstance(error, StrategyGenerationError):
            _strategy_http_event("generation_failed", category="strategy_generation_validation", status_code=422, generation_codes=error.code)
        elif isinstance(error, InvalidModelResponseError):
            _strategy_http_event("generation_failed", category="provider_response", status_code=502)
        elif isinstance(error, ProviderUnavailableError):
            _strategy_http_event("generation_failed", category="provider_unavailable", status_code=503)
        else:
            _strategy_http_event("generation_failed", category="provider_timeout", status_code=504)
        _generation_error(error)
    finally:
        db.close()
