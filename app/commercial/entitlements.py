"""The sole commercial-to-intelligence capability boundary."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.commercial.contracts import EntitlementDecision
from app.commercial.models import CURRENT_SUBSCRIPTION_STATUSES, Plan, PlanFeature, Subscription
from app.db.organization_orm import Organization


class EntitlementError(Exception):
    pass


class EntitlementOrganizationNotFoundError(EntitlementError):
    pass


class NoCurrentSubscriptionError(EntitlementError):
    pass


class EntitlementInactivePlanError(EntitlementError):
    pass


class EntitlementFeatureNotFoundError(EntitlementError):
    pass


class EntitlementFeatureDisabledError(EntitlementError):
    pass


class EntitlementFeatureTypeMismatchError(EntitlementError):
    pass


class EntitlementService:
    """Read-only resolver for an organization's active commercial capabilities."""

    def __init__(self, session: Session):
        self.session = session

    def get_entitlement(self, organization_id: int, feature_key: str) -> EntitlementDecision:
        self._require_organization(organization_id)
        subscription, plan = self._current_subscription_and_plan(organization_id)
        if subscription is None:
            return self._denied(organization_id, feature_key, "No current active or trialing subscription.")
        if not plan.is_active:
            return self._denied(organization_id, feature_key, "The subscription plan is inactive.", subscription, plan)

        feature = self.session.scalar(
            select(PlanFeature).where(PlanFeature.plan_id == plan.id, PlanFeature.feature_key == feature_key)
        )
        if feature is None:
            return self._denied(organization_id, feature_key, "Feature is not included in the subscription plan.", subscription, plan)
        return self._from_feature(organization_id, feature, subscription, plan)

    def has_feature(self, organization_id: int, feature_key: str) -> bool:
        result = self.get_entitlement(organization_id, feature_key)
        self._require_type(result, "boolean")
        return result.is_entitled

    def get_integer_limit(self, organization_id: int, feature_key: str) -> int | None:
        result = self.get_entitlement(organization_id, feature_key)
        self._require_type(result, "integer")
        return result.integer_value if result.is_entitled else None

    def get_decimal_limit(self, organization_id: int, feature_key: str):
        result = self.get_entitlement(organization_id, feature_key)
        self._require_type(result, "decimal")
        return result.decimal_value if result.is_entitled else None

    def get_string_value(self, organization_id: int, feature_key: str) -> str | None:
        result = self.get_entitlement(organization_id, feature_key)
        self._require_type(result, "string")
        return result.string_value if result.is_entitled else None

    def list_entitlements(self, organization_id: int) -> list[EntitlementDecision]:
        self._require_organization(organization_id)
        subscription, plan = self._current_subscription_and_plan(organization_id)
        if subscription is None or not plan.is_active:
            return []
        features = self.session.scalars(
            select(PlanFeature)
            .where(PlanFeature.plan_id == plan.id, PlanFeature.is_enabled.is_(True))
            .order_by(PlanFeature.feature_key)
        )
        return [self._from_feature(organization_id, feature, subscription, plan) for feature in features]

    def _require_organization(self, organization_id: int) -> Organization:
        organization = self.session.get(Organization, organization_id)
        if organization is None:
            raise EntitlementOrganizationNotFoundError(f"Organization {organization_id} was not found.")
        return organization

    def _current_subscription_and_plan(self, organization_id: int) -> tuple[Subscription | None, Plan | None]:
        row = self.session.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status.in_(CURRENT_SUBSCRIPTION_STATUSES),
            )
            .order_by(Subscription.starts_at.desc(), Subscription.id.desc())
        ).first()
        return (None, None) if row is None else row

    def _from_feature(self, organization_id: int, feature: PlanFeature, subscription: Subscription, plan: Plan) -> EntitlementDecision:
        values = {
            "boolean_value": None,
            "integer_value": None,
            "decimal_value": None,
            "string_value": None,
        }
        value = getattr(feature, f"{feature.value_type}_value")
        values[f"{feature.value_type}_value"] = value
        is_entitled = feature.is_enabled and value is not None
        if feature.value_type == "boolean":
            is_entitled = feature.is_enabled and value is True
        return EntitlementDecision(
            organization_id=organization_id,
            feature_key=feature.feature_key,
            is_entitled=is_entitled,
            value_type=feature.value_type,
            source_plan_id=plan.id,
            source_subscription_id=subscription.id,
            reason="Entitled." if is_entitled else "Feature value does not grant access.",
            **values,
        )

    def _denied(self, organization_id: int, feature_key: str, reason: str, subscription: Subscription | None = None, plan: Plan | None = None) -> EntitlementDecision:
        return EntitlementDecision(
            organization_id=organization_id,
            feature_key=feature_key,
            is_entitled=False,
            source_plan_id=plan.id if plan else None,
            source_subscription_id=subscription.id if subscription else None,
            reason=reason,
        )

    @staticmethod
    def _require_type(result: EntitlementDecision, expected_type: str) -> None:
        if result.value_type is not None and result.value_type != expected_type:
            raise EntitlementFeatureTypeMismatchError(
                f"Feature '{result.feature_key}' is {result.value_type}, not {expected_type}."
            )
