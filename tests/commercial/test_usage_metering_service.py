from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker

from app.commercial.metering import (
    UsageFeatureNotEntitledError, UsageFeatureNotMeteredError, UsageInvalidPeriodError,
    UsageInvalidQuantityError, UsageMeteringService, UsageNoCurrentSubscriptionError,
)
from app.commercial.models import Plan, PlanFeature, Subscription, UsageRecord
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


@pytest.fixture()
def session():
    engine=create_engine("sqlite:///:memory:"); event.listen(engine,"connect",lambda dbapi,_: dbapi.execute("PRAGMA foreign_keys=ON")); Base.metadata.create_all(engine)
    s=sessionmaker(bind=engine)(); s.execute(insert(user_table).values(id=1,email="meter@example.test",password_hash="test")); s.execute(insert(organization_table).values(id=1,name="Aura",slug="aura-meter",owner_user_id=1,plan="free",subscription_status="inactive",is_active=True))
    s.add(Plan(id=1,code="meter",name="Meter",seat_limit=1)); s.flush(); s.add_all([PlanFeature(plan_id=1,feature_key="api_calls",value_type="integer",integer_value=10),PlanFeature(plan_id=1,feature_key="budget",value_type="decimal",decimal_value=Decimal("5.5")),PlanFeature(plan_id=1,feature_key="flag",value_type="boolean",boolean_value=True),PlanFeature(plan_id=1,feature_key="disabled",value_type="integer",integer_value=1,is_enabled=False)]); s.commit()
    yield s; s.close(); engine.dispose()


def subscribe(session, status="active"):
    s=Subscription(organization_id=1,plan_id=1,status=status,billing_cycle="monthly",starts_at=datetime(2026,1,1,tzinfo=timezone.utc)); session.add(s); session.commit(); return s


def test_recording_idempotency_totals_and_remaining_limits(session):
    subscribe(session); service=UsageMeteringService(session); start=datetime(2026,1,1,tzinfo=timezone.utc); end=datetime(2026,2,1,tzinfo=timezone.utc)
    first=service.record_usage(organization_id=1,feature_key="api_calls",quantity=3,unit="request",occurred_at=datetime(2026,1,2,tzinfo=timezone.utc),idempotency_key="request-1",period_start=start,period_end=end)
    assert service.record_usage(organization_id=1,feature_key="api_calls",quantity=3,unit="request",occurred_at=datetime(2026,1,2,tzinfo=timezone.utc),idempotency_key="request-1") is first
    assert session.in_transaction(); session.commit()
    assert service.get_usage_total(1,"api_calls",period_start=start,period_end=end)==Decimal("3.0000")
    assert service.get_remaining_limit(1,"api_calls",period_start=start,period_end=end)==7
    service.record_usage(organization_id=1,feature_key="budget",quantity=Decimal("9"),unit="credit",occurred_at=datetime(2026,1,3,tzinfo=timezone.utc)); session.commit()
    assert service.get_remaining_limit(1,"budget",period_start=start,period_end=end)==Decimal("0")


def test_usage_service_rejections_and_rollback(session):
    service=UsageMeteringService(session)
    with pytest.raises(UsageNoCurrentSubscriptionError): service.record_usage(organization_id=1,feature_key="api_calls",quantity=1,unit="request",occurred_at=datetime.now(timezone.utc))
    subscribe(session,"trialing")
    with pytest.raises(UsageInvalidQuantityError): service.record_usage(organization_id=1,feature_key="api_calls",quantity=0,unit="request",occurred_at=datetime.now(timezone.utc))
    with pytest.raises(UsageFeatureNotEntitledError): service.record_usage(organization_id=1,feature_key="disabled",quantity=1,unit="request",occurred_at=datetime.now(timezone.utc))
    with pytest.raises(UsageFeatureNotMeteredError): service.record_usage(organization_id=1,feature_key="flag",quantity=1,unit="request",occurred_at=datetime.now(timezone.utc))
    with pytest.raises(UsageInvalidPeriodError): service.get_usage_total(1,"api_calls",period_start=datetime(2026,2,1,tzinfo=timezone.utc),period_end=datetime(2026,1,1,tzinfo=timezone.utc))
    record=service.record_usage(organization_id=1,feature_key="api_calls",quantity=1,unit="request",occurred_at=datetime.now(timezone.utc)); record_id=record.id; session.rollback(); assert session.get(UsageRecord,record_id) is None
