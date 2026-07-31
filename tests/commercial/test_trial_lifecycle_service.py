from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker

from app.commercial.entitlements import EntitlementService
from app.commercial.metering import UsageMeteringService, UsageNoCurrentSubscriptionError
from app.commercial.models import Plan, PlanFeature, Subscription, SubscriptionHistory, UsageRecord
from app.commercial.subscription_lifecycle import (
    CurrentSubscriptionAlreadyExistsError, InvalidTrialPeriodError,
    InvalidTrialStateTransitionError, SubscriptionLifecycleService,
    SubscriptionNotFoundError, SubscriptionPersistenceConflictError, TrialNotYetExpiredError,
)
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


START = datetime(2026, 7, 1, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine=create_engine("sqlite:///:memory:"); event.listen(engine,"connect",lambda dbapi,_: dbapi.execute("PRAGMA foreign_keys=ON")); Base.metadata.create_all(engine)
    s=sessionmaker(bind=engine)(); s.execute(insert(user_table).values(id=1,email="trial@example.test",password_hash="test")); s.execute(insert(organization_table).values(id=1,name="Aura",slug="aura-trial",owner_user_id=1,plan="free",subscription_status="inactive",is_active=True)); s.add(Plan(id=1,code="trial",name="Trial",seat_limit=1)); s.flush(); s.add(PlanFeature(plan_id=1,feature_key="api_calls",value_type="integer",integer_value=10)); s.commit()
    yield s; s.close(); engine.dispose()


def lifecycle(session, now=START): return SubscriptionLifecycleService(session, clock=lambda: now)
def as_utc(value): return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def test_start_trial_grants_access_and_usage(session):
    trial=lifecycle(session).start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta(days=7)); session.commit()
    assert (trial.status, as_utc(trial.starts_at), as_utc(trial.trial_ends_at))==("trialing",START,START+timedelta(days=7))
    assert session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id==trial.id)).one().event_type=="trial_started"
    assert EntitlementService(session).get_entitlement(1,"api_calls").is_entitled
    usage=UsageMeteringService(session).record_usage(organization_id=1,feature_key="api_calls",quantity=1,unit="request",occurred_at=START); session.commit(); assert usage.subscription_id==trial.id


def test_expire_trial_preserves_usage_and_revokes_access(session):
    trial=lifecycle(session).start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta(days=1)); session.commit()
    UsageMeteringService(session).record_usage(organization_id=1,feature_key="api_calls",quantity=1,unit="request",occurred_at=START); session.commit()
    with pytest.raises(TrialNotYetExpiredError): lifecycle(session).expire_trial(trial.id)
    expired=lifecycle(session,START+timedelta(days=1)).expire_trial(trial.id); session.commit()
    assert expired.status=="expired" and expired.version==2
    assert EntitlementService(session).get_entitlement(1,"api_calls").is_entitled is False
    with pytest.raises(UsageNoCurrentSubscriptionError): UsageMeteringService(session).record_usage(organization_id=1,feature_key="api_calls",quantity=1,unit="request",occurred_at=START+timedelta(days=1))
    assert len(session.scalars(select(UsageRecord).where(UsageRecord.subscription_id==trial.id)).all())==1
    assert session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id==trial.id,SubscriptionHistory.event_type=="trial_ended")).one().new_status=="expired"


def test_activate_trial_preserves_usage_and_history(session):
    trial=lifecycle(session).start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta(days=7)); session.commit()
    UsageMeteringService(session).record_usage(organization_id=1,feature_key="api_calls",quantity=1,unit="request",occurred_at=START); session.commit()
    active=lifecycle(session,START+timedelta(days=2)).activate_trial(trial.id); session.commit()
    assert active.status=="active" and active.version==2 and as_utc(active.trial_ends_at)==START+timedelta(days=7)
    assert EntitlementService(session).get_entitlement(1,"api_calls").is_entitled
    assert len(session.scalars(select(UsageRecord).where(UsageRecord.subscription_id==trial.id)).all())==1
    assert session.scalars(select(SubscriptionHistory).where(SubscriptionHistory.subscription_id==trial.id,SubscriptionHistory.event_type=="activated")).one().previous_status=="trialing"


def test_trial_validation_duplicate_rollback_and_history_failure(session, monkeypatch):
    with pytest.raises(InvalidTrialPeriodError): lifecycle(session).start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta())
    trial=lifecycle(session).start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta(days=1)); session.commit()
    with pytest.raises(CurrentSubscriptionAlreadyExistsError): lifecycle(session).start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta(days=1))
    with pytest.raises(SubscriptionNotFoundError): lifecycle(session).activate_trial(9999)
    lifecycle(session,START+timedelta(days=1)).expire_trial(trial.id); session.commit()
    before = len(session.scalars(select(Subscription)).all())
    failing=lifecycle(session); monkeypatch.setattr(failing.history,"save",lambda _: (_ for _ in ()).throw(RuntimeError("history failed")))
    with pytest.raises(SubscriptionPersistenceConflictError): failing.start_trial(organization_id=1,plan_id=1,billing_cycle="monthly",trial_duration=timedelta(days=1))
    assert len(session.scalars(select(Subscription)).all()) == before
