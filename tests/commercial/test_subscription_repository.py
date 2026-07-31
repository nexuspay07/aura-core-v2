from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.commercial.models import Plan, Subscription
from app.commercial.repositories import SqlAlchemySubscriptionRepository
from app.db.database import Base
from app.db.organization_orm import Organization
from app.db.organization_table import organization_table
from app.db.user_table import user_table


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    test_session.execute(insert(user_table).values(id=1, email="owner@example.test", password_hash="test"))
    test_session.execute(
        insert(organization_table).values(
            id=1, name="Aura", slug="aura", owner_user_id=1,
            plan="free", subscription_status="inactive", is_active=True,
        )
    )
    test_session.add_all([Plan(id=1, code="starter", name="Starter", seat_limit=1), Plan(id=2, code="pro", name="Pro", seat_limit=10)])
    test_session.commit()
    yield test_session
    test_session.close()
    engine.dispose()


def subscription(**overrides):
    starts_at = overrides.pop("starts_at", datetime(2026, 1, 1, tzinfo=timezone.utc))
    values = {
        "organization_id": 1,
        "plan_id": 1,
        "status": "active",
        "billing_cycle": "monthly",
        "starts_at": starts_at,
    }
    values.update(overrides)
    return Subscription(**values)


def test_subscription_repository_persists_current_subscription_and_relationships(session):
    repository = SqlAlchemySubscriptionRepository(session)
    saved = repository.save(subscription(external_reference="external-1"))
    session.commit()

    loaded = repository.get_by_id(saved.id)
    assert loaded is not None
    assert loaded.organization.name == "Aura"
    assert loaded.plan.code == "starter"
    assert repository.get_active_for_organization(1).id == saved.id
    assert repository.get_active_for_organization(999) is None
    assert [item.id for item in repository.list_for_organization(1)] == [saved.id]
    assert [item.id for item in repository.list_for_plan(1)] == [saved.id]
    assert Organization.__table__ is organization_table
    assert [item.id for item in loaded.organization.subscriptions] == [saved.id]
    assert [item.id for item in loaded.plan.subscriptions] == [saved.id]


def test_trialing_is_current_and_history_ordering_is_deterministic(session):
    repository = SqlAlchemySubscriptionRepository(session)
    historical = repository.save(subscription(status="cancelled", starts_at=datetime(2025, 1, 1, tzinfo=timezone.utc)))
    trialing = repository.save(subscription(status="trialing", plan_id=2, starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    session.commit()

    assert repository.get_active_for_organization(1).id == trialing.id
    assert [item.id for item in repository.list_for_organization(1)] == [trialing.id, historical.id]
    assert [item.id for item in repository.list_for_plan(2)] == [trialing.id]


def test_subscription_constraints_and_current_state_invariant(session):
    repository = SqlAlchemySubscriptionRepository(session)
    repository.save(subscription())
    session.commit()
    with pytest.raises(ValueError, match="only one active or trialing"):
        repository.save(subscription(status="trialing", plan_id=2))
    session.rollback()

    for invalid in (
        subscription(status="unknown"),
        subscription(billing_cycle="weekly"),
        subscription(ends_at=datetime(2025, 12, 31, tzinfo=timezone.utc)),
        subscription(plan_id=999, status="cancelled"),
        subscription(organization_id=999, status="cancelled"),
    ):
        session.add(invalid)
        with pytest.raises((IntegrityError, OperationalError)):
            session.flush()
        session.rollback()


def test_rollback_and_subscription_delete_preserve_parent_records(session):
    repository = SqlAlchemySubscriptionRepository(session)
    pending = repository.save(subscription(status="pending"))
    pending_id = pending.id
    session.rollback()
    assert repository.get_by_id(pending_id) is None

    saved = repository.save(subscription())
    session.commit()
    session.delete(saved)
    session.commit()
    assert session.get(Organization, 1) is not None
    assert session.get(Plan, 1) is not None
    assert session.execute(select(Subscription).where(Subscription.id == saved.id)).scalar_one_or_none() is None
