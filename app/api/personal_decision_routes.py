from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.api.auth_routes import get_current_user_from_token
from app.db.database import SessionLocal
from app.personal.decisions import (
    DECISION_STATUSES,
    DECISION_TYPES,
    OUTCOME_STATUSES,
    PersonalDecisionError,
    PersonalDecisionAlreadySavedError,
    PersonalDecisionNotFoundError,
    PersonalDecisionTransitionError,
    personal_decision_service,
)


router = APIRouter(prefix="/personal/decisions", tags=["Personal Decisions"])
security = HTTPBearer()


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
