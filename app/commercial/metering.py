"""Bounded, append-only commercial usage metering."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.commercial.entitlements import EntitlementService
from app.commercial.models import CURRENT_SUBSCRIPTION_STATUSES, Subscription, UsageRecord
from app.commercial.repositories import SqlAlchemyUsageRecordRepository
from app.db.organization_orm import Organization


class UsageMeteringError(Exception):
    pass


class UsageOrganizationNotFoundError(UsageMeteringError):
    pass


class UsageNoCurrentSubscriptionError(UsageMeteringError):
    pass


class UsageFeatureNotEntitledError(UsageMeteringError):
    pass


class UsageFeatureNotMeteredError(UsageMeteringError):
    pass


class UsageInvalidQuantityError(UsageMeteringError):
    pass


class UsageInvalidPeriodError(UsageMeteringError):
    pass


class UsageIdempotencyConflictError(UsageMeteringError):
    pass


class UsagePersistenceConflictError(UsageMeteringError):
    pass


class UsageMeteringService:
    """Records entitled metered use without commits or overage handling.

    Idempotency is protected by a portable database unique constraint. Limit
    enforcement is read-then-write and can race across independent transactions;
    this service does not claim hard concurrency-safe limit enforcement.
    """

    def __init__(self, session: Session, *, repository: SqlAlchemyUsageRecordRepository | None = None, entitlement_service: EntitlementService | None = None):
        self.session = session
        self.records = repository or SqlAlchemyUsageRecordRepository(session)
        self.entitlements = entitlement_service or EntitlementService(session)

    def record_usage(
        self,
        *,
        organization_id: int,
        feature_key: str,
        quantity: Decimal | int | float | str,
        unit: str,
        occurred_at: datetime,
        idempotency_key: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        metadata_json: dict | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> UsageRecord:
        self._require_organization(organization_id)
        self._validate_period(period_start, period_end)
        if period_start is not None and not (period_start <= occurred_at < period_end):
            raise UsageInvalidPeriodError("occurred_at must be within the supplied period.")
        quantity_decimal = self._positive_quantity(quantity)
        if not unit:
            raise UsagePersistenceConflictError("Usage unit is required.")
        subscription = self._current_subscription(organization_id)
        if subscription is None:
            raise UsageNoCurrentSubscriptionError("Organization has no current active or trialing subscription.")
        entitlement = self.entitlements.get_entitlement(organization_id, feature_key)
        if not entitlement.is_entitled:
            raise UsageFeatureNotEntitledError(entitlement.reason)
        if entitlement.value_type not in {"integer", "decimal"}:
            raise UsageFeatureNotMeteredError(f"Feature '{feature_key}' is not an integer or decimal metered feature.")
        if idempotency_key:
            existing = self.records.get_by_idempotency_key(organization_id, idempotency_key)
            if existing is not None:
                return existing
        record = UsageRecord(
            organization_id=organization_id,
            subscription_id=subscription.id,
            feature_key=feature_key,
            quantity=quantity_decimal,
            unit=unit,
            occurred_at=occurred_at,
            idempotency_key=idempotency_key,
            source_type=source_type,
            source_id=source_id,
            metadata_json=metadata_json,
            created_at=occurred_at,
        )
        try:
            return self.records.save(record)
        except Exception as exc:
            self.session.rollback()
            if idempotency_key:
                existing = self.records.get_by_idempotency_key(organization_id, idempotency_key)
                if existing is not None:
                    return existing
            raise UsagePersistenceConflictError("Unable to persist usage record.") from exc

    def get_usage_total(self, organization_id: int, feature_key: str, *, period_start: datetime, period_end: datetime) -> Decimal:
        self._require_organization(organization_id)
        self._validate_period(period_start, period_end)
        return self.records.sum_for_organization_feature(organization_id, feature_key, period_start, period_end)

    def get_remaining_limit(self, organization_id: int, feature_key: str, *, period_start: datetime, period_end: datetime):
        self._validate_period(period_start, period_end)
        entitlement = self.entitlements.get_entitlement(organization_id, feature_key)
        if not entitlement.is_entitled:
            raise UsageFeatureNotEntitledError(entitlement.reason)
        if entitlement.value_type == "integer":
            limit = Decimal(entitlement.integer_value)
        elif entitlement.value_type == "decimal":
            limit = Decimal(entitlement.decimal_value)
        else:
            raise UsageFeatureNotMeteredError(f"Feature '{feature_key}' is not metered.")
        remaining = max(limit - self.get_usage_total(organization_id, feature_key, period_start=period_start, period_end=period_end), Decimal("0"))
        return int(remaining) if entitlement.value_type == "integer" else remaining

    def _require_organization(self, organization_id: int) -> Organization:
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise UsageOrganizationNotFoundError(f"Organization {organization_id} was not found.")
        return organization

    def _current_subscription(self, organization_id: int) -> Subscription | None:
        return self.session.query(Subscription).filter(Subscription.organization_id == organization_id, Subscription.status.in_(CURRENT_SUBSCRIPTION_STATUSES)).order_by(Subscription.starts_at.desc(), Subscription.id.desc()).first()

    @staticmethod
    def _positive_quantity(quantity) -> Decimal:
        try:
            value = Decimal(str(quantity))
        except (InvalidOperation, ValueError) as exc:
            raise UsageInvalidQuantityError("Usage quantity must be a positive number.") from exc
        if value <= 0:
            raise UsageInvalidQuantityError("Usage quantity must be positive.")
        return value

    @staticmethod
    def _validate_period(period_start: datetime | None, period_end: datetime | None) -> None:
        if (period_start is None) != (period_end is None) or (period_start is not None and period_end <= period_start):
            raise UsageInvalidPeriodError("period_end must be later than period_start.")
