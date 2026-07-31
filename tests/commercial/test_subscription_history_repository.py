from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.commercial.models import Plan, Subscription, SubscriptionHistory
from app.commercial.repositories import SqlAlchemySubscriptionHistoryRepository
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
    test_session.execute(insert(user_table).values(id=1, email="history-owner@example.test", password_hash="test"))
    test_session.execute(insert(organization_table).values(id=1, name="Aura", slug="aura-history", owner_user_id=1, plan="free", subscription_status="inactive", is_active=True))
    test_session.add_all([Plan(id=1, code="history", name="History", seat_limit=1), Plan(id=2, code="history-next", name="History Next", seat_limit=2)])
    test_session.flush()
    test_session.add(Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    test_session.commit()
    yield test_session
    test_session.close()
    engine.dispose()


def history(**overrides):
    values = {
        "subscription_id": 1,
        "event_type": "activated",
        "new_status": "active",
        "effective_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return SubscriptionHistory(**values)


def test_history_repository_saves_loads_orders_and_loads_relationship(session):
    repository = SqlAlchemySubscriptionHistoryRepository(session)
    later = repository.save(history(event_type="renewed", effective_at=datetime(2026, 2, 1, tzinfo=timezone.utc)))
    earlier = repository.save(history(event_type="created", effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc), new_status=None))
    session.commit()

    assert repository.get_by_id(earlier.id).subscription.id == 1
    assert [item.id for item in repository.list_for_subscription(1)] == [earlier.id, later.id]
    assert [item.id for item in repository.list_by_event_type("renewed")] == [later.id]
    assert [item.id for item in session.get(Subscription, 1).history] == [earlier.id, later.id]


def test_history_constraints_and_restrictive_subscription_delete(session):
    repository = SqlAlchemySubscriptionHistoryRepository(session)
    repository.save(history(previous_plan_id=1, new_plan_id=2, event_type="plan_changed", new_status=None))
    session.commit()

    for invalid in (
        history(event_type="unknown"),
        history(previous_status="unknown"),
        history(new_status="unknown"),
        history(previous_plan_id=999, event_type="plan_changed", new_status=None),
        history(subscription_id=999),
    ):
        session.add(invalid)
        with pytest.raises((IntegrityError, OperationalError)):
            session.flush()
        session.rollback()

    session.delete(session.get(Subscription, 1))
    with pytest.raises((IntegrityError, OperationalError)):
        session.commit()
    session.rollback()


def test_history_repository_is_append_only_and_direct_delete_preserves_subscription(session):
    repository = SqlAlchemySubscriptionHistoryRepository(session)
    record = repository.save(history())
    record_id = record.id
    session.rollback()
    assert repository.get_by_id(record_id) is None
    assert not hasattr(repository, "update")
    assert not hasattr(repository, "delete")

    record = repository.save(history())
    session.commit()
    session.delete(record)
    session.commit()
    assert session.get(Subscription, 1) is not None
