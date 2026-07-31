from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.commercial.models import Plan, Subscription, UsageRecord
from app.commercial.repositories import SqlAlchemyUsageRecordRepository
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.execute(insert(user_table).values(id=1, email="usage@example.test", password_hash="test"))
    s.execute(insert(organization_table).values(id=1, name="Aura", slug="aura-usage", owner_user_id=1, plan="free", subscription_status="inactive", is_active=True))
    s.add(Plan(id=1, code="usage", name="Usage", seat_limit=1))
    s.flush()
    s.add(Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    s.commit()
    yield s
    s.close(); engine.dispose()


def record(**values):
    base = dict(organization_id=1, subscription_id=1, feature_key="api_calls", quantity=Decimal("2.5"), unit="request", occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    base.update(values)
    return UsageRecord(**base)


def test_usage_repository_persists_relationships_lists_and_sql_totals(session):
    repo = SqlAlchemyUsageRecordRepository(session)
    first = repo.save(record(idempotency_key="one"))
    second = repo.save(record(quantity=Decimal("3"), occurred_at=datetime(2026, 1, 3, tzinfo=timezone.utc), idempotency_key="two"))
    session.commit()
    assert repo.get_by_id(first.id).organization.name == "Aura"
    assert repo.get_by_id(first.id).subscription.id == 1
    assert repo.get_by_idempotency_key(1, "one").id == first.id
    assert [item.id for item in repo.list_for_organization(1)] == [first.id, second.id]
    assert [item.id for item in repo.list_for_subscription(1)] == [first.id, second.id]
    start, end = datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc)
    assert repo.sum_for_organization_feature(1, "api_calls", start, end) == Decimal("5.5000")
    assert repo.sum_for_subscription_feature(1, "api_calls", start, end) == Decimal("5.5000")
    assert len(repo.list_within_period(1, start, end)) == 2
    assert not hasattr(repo, "update") and not hasattr(repo, "delete")


def test_usage_repository_constraints_and_scoped_idempotency(session):
    repo = SqlAlchemyUsageRecordRepository(session)
    for invalid in (record(quantity=0), record(quantity=-1), record(organization_id=999), record(subscription_id=999)):
        session.add(invalid)
        with pytest.raises((IntegrityError, OperationalError)):
            session.flush()
        session.rollback()
    repo.save(record(idempotency_key="duplicate")); session.commit()
    with pytest.raises(IntegrityError):
        repo.save(record(idempotency_key="duplicate"))
    session.rollback()
