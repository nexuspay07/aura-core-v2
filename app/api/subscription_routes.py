"""HTTP boundary for the existing subscription lifecycle service."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.auth_routes import get_current_user_from_token
from app.commercial.models import Subscription, SubscriptionHistory
from app.commercial.repositories import SqlAlchemySubscriptionHistoryRepository, SqlAlchemySubscriptionRepository
from app.commercial.subscription_lifecycle import SubscriptionLifecycleError, SubscriptionLifecycleService
from app.db.database import SessionLocal

router = APIRouter(prefix="/commercial/subscriptions", tags=["Commercial Subscriptions"])
security = HTTPBearer()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def current(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await get_current_user_from_token(credentials)


def organization_id(user) -> int:
    organization = user.get("organization")
    if not organization:
        raise HTTPException(403, "No active organization")
    return organization["id"]


def owned(subscription: Subscription | None, user) -> Subscription:
    if subscription is None or subscription.organization_id != organization_id(user):
        raise HTTPException(404, "Subscription not found")
    return subscription


def write(session: Session, operation):
    try:
        result = operation()
        session.commit()
        session.refresh(result)
        return result
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise


def lifecycle(operation):
    try:
        return operation()
    except SubscriptionLifecycleError as exc:
        raise HTTPException(409, "Subscription operation rejected") from exc


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    organization_id: int | None = None
    plan_id: int
    billing_cycle: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    renews_at: datetime | None = None
    trial_ends_at: datetime | None = None
    external_reference: str | None = None


class SubscriptionTrialCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    organization_id: int | None = None
    plan_id: int
    billing_cycle: str
    trial_ends_at: datetime
    external_reference: str | None = None


class ActivationRequest(BaseModel):
    renews_at: datetime | None = None


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    plan_id: int
    status: str
    billing_cycle: str
    starts_at: datetime
    ends_at: datetime | None
    renews_at: datetime | None
    cancelled_at: datetime | None
    trial_ends_at: datetime | None
    external_reference: str | None
    version: int


class SubscriptionHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscription_id: int
    event_type: str
    previous_status: str | None
    new_status: str | None
    previous_plan_id: int | None
    new_plan_id: int | None
    effective_at: datetime
    reason: str | None
    external_reference: str | None


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(session: Session = Depends(get_session), user=Depends(current)):
    return SqlAlchemySubscriptionRepository(session).list_for_organization(organization_id(user))


@router.post("", status_code=201, response_model=SubscriptionOut)
def create_subscription(body: SubscriptionCreate, session: Session = Depends(get_session), user=Depends(current)):
    data = body.model_dump()
    data["organization_id"] = organization_id(user)
    return write(session, lambda: lifecycle(lambda: SubscriptionLifecycleService(session).create_pending_subscription(**data)))


@router.post("/trial", status_code=201, response_model=SubscriptionOut)
def start_trial(body: SubscriptionTrialCreate, session: Session = Depends(get_session), user=Depends(current)):
    data = body.model_dump()
    data["organization_id"] = organization_id(user)
    return write(session, lambda: lifecycle(lambda: SubscriptionLifecycleService(session).start_trial(**data)))


@router.get("/{subscription_id}", response_model=SubscriptionOut)
def get_subscription(subscription_id: int, session: Session = Depends(get_session), user=Depends(current)):
    return owned(SqlAlchemySubscriptionRepository(session).get_by_id(subscription_id), user)


@router.get("/{subscription_id}/history", response_model=list[SubscriptionHistoryOut])
def get_history(subscription_id: int, session: Session = Depends(get_session), user=Depends(current)):
    owned(SqlAlchemySubscriptionRepository(session).get_by_id(subscription_id), user)
    return SqlAlchemySubscriptionHistoryRepository(session).list_for_subscription(subscription_id)


@router.post("/{subscription_id}/activate", response_model=SubscriptionOut)
def activate(subscription_id: int, body: ActivationRequest, session: Session = Depends(get_session), user=Depends(current)):
    owned(SqlAlchemySubscriptionRepository(session).get_by_id(subscription_id), user)
    return write(session, lambda: lifecycle(lambda: SubscriptionLifecycleService(session).activate_subscription(subscription_id, renews_at=body.renews_at)))


@router.post("/{subscription_id}/activate-trial", response_model=SubscriptionOut)
def activate_trial(subscription_id: int, body: ActivationRequest, session: Session = Depends(get_session), user=Depends(current)):
    owned(SqlAlchemySubscriptionRepository(session).get_by_id(subscription_id), user)
    return write(session, lambda: lifecycle(lambda: SubscriptionLifecycleService(session).activate_trial(subscription_id, renews_at=body.renews_at)))


@router.post("/{subscription_id}/expire-trial", response_model=SubscriptionOut)
def expire_trial(subscription_id: int, session: Session = Depends(get_session), user=Depends(current)):
    owned(SqlAlchemySubscriptionRepository(session).get_by_id(subscription_id), user)
    return write(session, lambda: lifecycle(lambda: SubscriptionLifecycleService(session).expire_trial(subscription_id)))
