from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker

from app.commercial.models import Plan, Subscription, SubscriptionHistory
from app.commercial.subscription_lifecycle import (
    CurrentSubscriptionAlreadyExistsError,
    InactivePlanError,
    InvalidSubscriptionStateTransitionError,
    OrganizationNotFoundError,
    PlanNotFoundError,
    SubscriptionLifecycleService,
    SubscriptionNotFoundError,
    SubscriptionPersistenceConflictError,
)
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


FIXED_TIME = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    test_session.execute(insert(user_table).values(id=1, email="lifecycle-owner@example.test", password_hash="test"))
    test_session.execute(insert(organization_table).values(id=1, name="Aura", slug="aura-lifecycle", owner_user_id=1, plan="free", subscription_status="inactive", is_active=True))
    test_session.add_all([
        Plan(id=1, code="lifecycle", name="Lifecycle", seat_limit=1, is_active=True),
        Plan(id=2, code="inactive", name="Inactive", seat_limit=1, is_active=False),
    ])
    test_session.commit()
    yield test_session
    test_session.close()
    engine.dispose()


def service(session, clock=lambda: FIXED_TIME):
    return SubscriptionLifecycleService(session, clock=clock)


def as_utc(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def test_create_pending_subscription_writes_matching_history_at_one_timestamp(session):
    lifecycle = service(session)
    subscription = lifecycle.create_pending_subscription(organization_id=1, plan_id=1, billing_cycle="monthly")

    assert subscription.status == "pending"
    assert subscription.starts_at == FIXED_TIME
    assert subscription.created_at == FIXED_TIME
    assert subscription.updated_at == FIXED_TIME
    assert session.in_transaction()
    session.commit()

    history = session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id == subscription.id)).one()
    assert (history.event_type, history.new_status, as_utc(history.effective_at), as_utc(history.created_at)) == ("created", "pending", FIXED_TIME, FIXED_TIME)


def test_activation_writes_history_increments_version_and_caller_rollback_restores_pending(session):
    lifecycle = service(session)
    pending = lifecycle.create_pending_subscription(organization_id=1, plan_id=1, billing_cycle="monthly")
    session.commit()

    activation_time = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    activated = service(session, clock=lambda: activation_time).activate_subscription(pending.id)
    assert activated.status == "active"
    assert activated.version == 2
    assert activated.updated_at == activation_time
    history = session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id == pending.id, SubscriptionHistory.event_type == "activated")).one()
    assert (history.previous_status, history.new_status, as_utc(history.effective_at)) == ("pending", "active", activation_time)

    session.rollback()
    restored = session.get(Subscription, pending.id)
    assert restored.status == "pending"
    assert restored.version == 1
    assert len(session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id == pending.id)).all()) == 1


def test_lifecycle_rejections_and_duplicate_current_subscription(session):
    lifecycle = service(session)
    with pytest.raises(OrganizationNotFoundError):
        lifecycle.create_pending_subscription(organization_id=999, plan_id=1, billing_cycle="monthly")
    with pytest.raises(PlanNotFoundError):
        lifecycle.create_pending_subscription(organization_id=1, plan_id=999, billing_cycle="monthly")
    with pytest.raises(InactivePlanError):
        lifecycle.create_pending_subscription(organization_id=1, plan_id=2, billing_cycle="monthly")
    with pytest.raises(SubscriptionNotFoundError):
        lifecycle.activate_subscription(999)

    active = Subscription(organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=FIXED_TIME)
    session.add(active)
    session.commit()
    with pytest.raises(CurrentSubscriptionAlreadyExistsError):
        lifecycle.create_pending_subscription(organization_id=1, plan_id=1, billing_cycle="monthly")
    with pytest.raises(InvalidSubscriptionStateTransitionError):
        lifecycle.activate_subscription(active.id)

    active.status = "cancelled"
    session.commit()
    with pytest.raises(InvalidSubscriptionStateTransitionError):
        lifecycle.activate_subscription(active.id)


def test_history_write_failure_rolls_back_create_and_activation(session, monkeypatch):
    lifecycle = service(session)
    monkeypatch.setattr(lifecycle.history, "save", lambda _: (_ for _ in ()).throw(RuntimeError("history unavailable")))
    with pytest.raises(SubscriptionPersistenceConflictError):
        lifecycle.create_pending_subscription(organization_id=1, plan_id=1, billing_cycle="monthly")
    assert session.scalars(select(Subscription)).all() == []
    assert session.scalars(select(SubscriptionHistory)).all() == []

    lifecycle = service(session)
    pending = lifecycle.create_pending_subscription(organization_id=1, plan_id=1, billing_cycle="monthly")
    session.commit()
    monkeypatch.setattr(lifecycle.history, "save", lambda _: (_ for _ in ()).throw(RuntimeError("history unavailable")))
    with pytest.raises(SubscriptionPersistenceConflictError):
        lifecycle.activate_subscription(pending.id)
    assert session.get(Subscription, pending.id).status == "pending"
    assert len(session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id == pending.id)).all()) == 1


def test_caller_rollback_removes_pending_subscription_and_matching_history(session):
    pending = service(session).create_pending_subscription(organization_id=1, plan_id=1, billing_cycle="monthly")
    pending_id = pending.id
    session.rollback()
    assert session.get(Subscription, pending_id) is None
    assert session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id == pending_id)).all() == []
