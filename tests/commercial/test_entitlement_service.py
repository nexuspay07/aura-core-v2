from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker

from app.commercial.entitlements import (
    EntitlementFeatureTypeMismatchError,
    EntitlementOrganizationNotFoundError,
    EntitlementService,
)
from app.commercial.models import Plan, PlanFeature, Subscription
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    test_session.execute(insert(user_table).values(id=1, email="entitlements@example.test", password_hash="test"))
    test_session.execute(insert(organization_table).values(id=1, name="Aura", slug="aura-entitlements", owner_user_id=1, plan="free", subscription_status="inactive", is_active=True))
    plan = Plan(id=1, code="entitlement", name="Entitlement", seat_limit=10, is_active=True)
    test_session.add(plan)
    test_session.add_all([
        PlanFeature(plan_id=1, feature_key="automation", value_type="boolean", boolean_value=True),
        PlanFeature(plan_id=1, feature_key="disabled", value_type="boolean", boolean_value=True, is_enabled=False),
        PlanFeature(plan_id=1, feature_key="max_users", value_type="integer", integer_value=25),
        PlanFeature(plan_id=1, feature_key="budget", value_type="decimal", decimal_value=Decimal("12.50")),
        PlanFeature(plan_id=1, feature_key="tier_name", value_type="string", string_value="executive"),
        PlanFeature(plan_id=1, feature_key="false_flag", value_type="boolean", boolean_value=False),
    ])
    test_session.commit()
    yield test_session
    test_session.close()
    engine.dispose()


def add_subscription(session, status="active"):
    subscription = Subscription(
        organization_id=1,
        plan_id=1,
        status=status,
        billing_cycle="monthly",
        starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    session.add(subscription)
    session.commit()
    return subscription


def test_active_and_trialing_subscriptions_grant_typed_entitlements(session):
    add_subscription(session, "active")
    resolver = EntitlementService(session)
    boolean = resolver.get_entitlement(1, "automation")
    assert boolean.is_entitled and boolean.boolean_value is True and boolean.integer_value is None
    assert resolver.has_feature(1, "automation") is True
    assert resolver.get_integer_limit(1, "max_users") == 25
    assert resolver.get_decimal_limit(1, "budget") == Decimal("12.5000")
    assert resolver.get_string_value(1, "tier_name") == "executive"

    session.get(Subscription, 1).status = "trialing"
    session.commit()
    assert resolver.get_entitlement(1, "automation").is_entitled is True


@pytest.mark.parametrize("status", ["pending", "paused", "past_due", "cancelled", "expired"])
def test_non_current_subscription_statuses_do_not_grant_access(session, status):
    add_subscription(session, status)
    result = EntitlementService(session).get_entitlement(1, "automation")
    assert result.is_entitled is False
    assert result.reason == "No current active or trialing subscription."


def test_denial_results_for_no_subscription_missing_disabled_false_and_inactive_plan(session):
    resolver = EntitlementService(session)
    assert resolver.get_entitlement(1, "automation").is_entitled is False

    add_subscription(session)
    assert resolver.get_entitlement(1, "missing").is_entitled is False
    assert resolver.get_entitlement(1, "disabled").is_entitled is False
    assert resolver.has_feature(1, "false_flag") is False

    session.get(Plan, 1).is_active = False
    session.commit()
    assert resolver.get_entitlement(1, "automation").is_entitled is False


def test_missing_organization_and_type_mismatches_are_explicit(session):
    add_subscription(session)
    resolver = EntitlementService(session)
    with pytest.raises(EntitlementOrganizationNotFoundError):
        resolver.get_entitlement(999, "automation")
    with pytest.raises(EntitlementFeatureTypeMismatchError):
        resolver.has_feature(1, "max_users")
    with pytest.raises(EntitlementFeatureTypeMismatchError):
        resolver.get_string_value(1, "budget")


def test_listing_excludes_disabled_features_and_resolution_is_read_only(session):
    add_subscription(session)
    resolver = EntitlementService(session)
    before = (len(session.new), len(session.dirty), len(session.deleted))
    results = resolver.list_entitlements(1)
    assert {result.feature_key for result in results} == {
        "automation", "budget", "false_flag", "max_users", "tier_name"
    }
    assert all(result.feature_key != "disabled" for result in results)
    assert (len(session.new), len(session.dirty), len(session.deleted)) == before

    session.rollback()
    assert resolver.get_entitlement(1, "automation").is_entitled is True
