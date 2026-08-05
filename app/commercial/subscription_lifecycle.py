"""Bounded, session-scoped Subscription lifecycle operations."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.commercial.models import Subscription, SubscriptionHistory
from app.commercial.repositories import (
    SqlAlchemySubscriptionHistoryRepository,
    SqlAlchemySubscriptionRepository,
)
from app.db.organization_orm import Organization
from app.commercial.models import Plan


class SubscriptionLifecycleError(Exception):
    """Base class for application-level lifecycle outcomes."""


class OrganizationNotFoundError(SubscriptionLifecycleError):
    pass


class PlanNotFoundError(SubscriptionLifecycleError):
    pass


class InactivePlanError(SubscriptionLifecycleError):
    pass


class SubscriptionNotFoundError(SubscriptionLifecycleError):
    pass


class InvalidSubscriptionStateTransitionError(SubscriptionLifecycleError):
    pass


class CurrentSubscriptionAlreadyExistsError(SubscriptionLifecycleError):
    pass


class SubscriptionPersistenceConflictError(SubscriptionLifecycleError):
    pass


class InvalidTrialPeriodError(SubscriptionLifecycleError):
    pass


class TrialNotYetExpiredError(SubscriptionLifecycleError):
    pass


class InvalidTrialStateTransitionError(SubscriptionLifecycleError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class SubscriptionLifecycleService:
    """Creates pending subscriptions and activates them without committing.

    The one-current-subscription check is transaction-local and remains subject
    to the repository's documented cross-transaction concurrency limitation.
    """

    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[[], datetime] = utc_now,
        subscription_repository: SqlAlchemySubscriptionRepository | None = None,
        history_repository: SqlAlchemySubscriptionHistoryRepository | None = None,
    ):
        self.session = session
        self.clock = clock
        self.subscriptions = subscription_repository or SqlAlchemySubscriptionRepository(session)
        self.history = history_repository or SqlAlchemySubscriptionHistoryRepository(session)

    def create_pending_subscription(
        self,
        *,
        organization_id: int,
        plan_id: int,
        billing_cycle: str,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        renews_at: datetime | None = None,
        trial_ends_at: datetime | None = None,
        external_reference: str | None = None,
    ) -> Subscription:
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise OrganizationNotFoundError(f"Organization {organization_id} was not found.")
        plan = self.session.get(Plan, plan_id)
        if plan is None:
            raise PlanNotFoundError(f"Plan {plan_id} was not found.")
        if not plan.is_active:
            raise InactivePlanError(f"Plan {plan_id} is inactive.")
        if self.subscriptions.get_active_for_organization(organization_id) is not None:
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.")

        operation_time = self.clock()
        subscription = Subscription(
            organization_id=organization_id,
            plan_id=plan_id,
            status="pending",
            billing_cycle=billing_cycle,
            starts_at=starts_at or operation_time,
            ends_at=ends_at,
            renews_at=renews_at,
            trial_ends_at=trial_ends_at,
            external_reference=external_reference,
            created_at=operation_time,
            updated_at=operation_time,
        )
        try:
            self.subscriptions.save(subscription)
            self.history.save(
                SubscriptionHistory(
                    subscription_id=subscription.id,
                    event_type="created",
                    new_status="pending",
                    effective_at=operation_time,
                    external_reference=external_reference,
                    created_at=operation_time,
                )
            )
            return subscription
        except (SubscriptionLifecycleError, CurrentSubscriptionAlreadyExistsError):
            raise
        except ValueError as exc:
            self.session.rollback()
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.") from exc
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionPersistenceConflictError("Unable to create the pending subscription.") from exc

    def activate_subscription(
        self,
        subscription_id: int,
        *,
        renews_at: datetime | None = None,
    ) -> Subscription:
        subscription = self.subscriptions.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} was not found.")
        if subscription.status != "pending":
            raise InvalidSubscriptionStateTransitionError("Only pending subscriptions may be activated.")
        current = self.subscriptions.get_active_for_organization(subscription.organization_id)
        if current is not None and current.id != subscription.id:
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.")

        operation_time = self.clock()
        previous_status = subscription.status
        subscription.status = "active"
        subscription.version += 1
        subscription.updated_at = operation_time
        if renews_at is not None:
            subscription.renews_at = renews_at
        try:
            self.subscriptions.save(subscription)
            self.history.save(
                SubscriptionHistory(
                    subscription_id=subscription.id,
                    event_type="activated",
                    previous_status=previous_status,
                    new_status="active",
                    effective_at=operation_time,
                    created_at=operation_time,
                )
            )
            return subscription
        except ValueError as exc:
            self.session.rollback()
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.") from exc
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionPersistenceConflictError("Unable to activate the subscription.") from exc

    def start_trial(
        self,
        *,
        organization_id: int,
        plan_id: int,
        billing_cycle: str,
        trial_duration: timedelta | None = None,
        trial_ends_at: datetime | None = None,
        external_reference: str | None = None,
    ) -> Subscription:
        if self.session.get(Organization, organization_id) is None:
            raise OrganizationNotFoundError(f"Organization {organization_id} was not found.")
        plan = self.session.get(Plan, plan_id)
        if plan is None:
            raise PlanNotFoundError(f"Plan {plan_id} was not found.")
        if not plan.is_active:
            raise InactivePlanError(f"Plan {plan_id} is inactive.")
        if self.subscriptions.get_active_for_organization(organization_id) is not None:
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.")
        operation_time = self.clock()
        calculated_end = trial_ends_at or (operation_time + trial_duration if trial_duration is not None else None)
        if calculated_end is None or calculated_end <= operation_time:
            raise InvalidTrialPeriodError("trial_ends_at must be later than the trial start time.")
        subscription = Subscription(
            organization_id=organization_id,
            plan_id=plan_id,
            status="trialing",
            billing_cycle=billing_cycle,
            starts_at=operation_time,
            trial_ends_at=calculated_end,
            external_reference=external_reference,
            created_at=operation_time,
            updated_at=operation_time,
        )
        try:
            self.subscriptions.save(subscription)
            self.history.save(SubscriptionHistory(subscription_id=subscription.id, event_type="trial_started", new_status="trialing", effective_at=operation_time, external_reference=external_reference, created_at=operation_time))
            return subscription
        except ValueError as exc:
            self.session.rollback()
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.") from exc
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionPersistenceConflictError("Unable to start the trial.") from exc

    def expire_trial(self, subscription_id: int) -> Subscription:
        subscription = self.subscriptions.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} was not found.")
        if subscription.status != "trialing" or subscription.trial_ends_at is None:
            raise InvalidTrialStateTransitionError("Only trialing subscriptions with an end time may expire.")
        operation_time = self.clock()
        if operation_time < _as_utc(subscription.trial_ends_at):
            raise TrialNotYetExpiredError("The trial has not reached its expiry time.")
        subscription.status = "expired"; subscription.version += 1; subscription.updated_at = operation_time
        try:
            self.subscriptions.save(subscription)
            self.history.save(SubscriptionHistory(subscription_id=subscription.id, event_type="trial_ended", previous_status="trialing", new_status="expired", effective_at=operation_time, created_at=operation_time))
            return subscription
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionPersistenceConflictError("Unable to expire the trial.") from exc

    def suspend_subscription(self, subscription_id: int) -> Subscription:
        return self._transition(subscription_id, {"active"}, "paused", "paused")

    def resume_subscription(self, subscription_id: int) -> Subscription:
        return self._transition(subscription_id, {"paused"}, "active", "resumed")

    def cancel_subscription(self, subscription_id: int) -> Subscription:
        return self._transition(subscription_id, {"trialing", "active", "paused"}, "cancelled", "cancelled", set_cancelled=True)

    def expire_subscription(self, subscription_id: int) -> Subscription:
        subscription = self.subscriptions.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} was not found.")
        if subscription.status != "active" or subscription.ends_at is None or self.clock() < _as_utc(subscription.ends_at):
            raise InvalidSubscriptionStateTransitionError("Only ended active subscriptions may expire.")
        return self._transition(subscription_id, {"active"}, "expired", "expired")

    def _transition(self, subscription_id: int, allowed: set[str], target: str, event_type: str, *, set_cancelled: bool = False) -> Subscription:
        subscription = self.subscriptions.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} was not found.")
        if subscription.status not in allowed:
            raise InvalidSubscriptionStateTransitionError("Invalid subscription state transition.")
        operation_time = self.clock(); previous = subscription.status
        subscription.status = target; subscription.version += 1; subscription.updated_at = operation_time
        if set_cancelled: subscription.cancelled_at = operation_time
        try:
            self.subscriptions.save(subscription)
            self.history.save(SubscriptionHistory(subscription_id=subscription.id, event_type=event_type, previous_status=previous, new_status=target, effective_at=operation_time, created_at=operation_time))
            return subscription
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionPersistenceConflictError("Unable to transition the subscription.") from exc

    def activate_trial(self, subscription_id: int, *, renews_at: datetime | None = None) -> Subscription:
        subscription = self.subscriptions.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(f"Subscription {subscription_id} was not found.")
        if subscription.status != "trialing":
            raise InvalidTrialStateTransitionError("Only trialing subscriptions may be activated as trials.")
        current = self.subscriptions.get_active_for_organization(subscription.organization_id)
        if current is not None and current.id != subscription.id:
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.")
        operation_time = self.clock()
        subscription.status = "active"; subscription.version += 1; subscription.updated_at = operation_time
        if renews_at is not None: subscription.renews_at = renews_at
        try:
            self.subscriptions.save(subscription)
            self.history.save(SubscriptionHistory(subscription_id=subscription.id, event_type="activated", previous_status="trialing", new_status="active", effective_at=operation_time, created_at=operation_time))
            return subscription
        except ValueError as exc:
            self.session.rollback()
            raise CurrentSubscriptionAlreadyExistsError("The organization already has a current subscription.") from exc
        except Exception as exc:
            self.session.rollback()
            raise SubscriptionPersistenceConflictError("Unable to activate the trial.") from exc
