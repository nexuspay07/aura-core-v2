"""Real HTTP integration tests for the supported subscription lifecycle."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import app.api.subscription_routes as routes
from app.api.subscription_routes import current, router
from app.commercial.models import Plan, Subscription, SubscriptionHistory
from app.commercial.subscription_lifecycle import SubscriptionLifecycleService
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


NOW = datetime(2026, 7, 30, tzinfo=timezone.utc)


@pytest.fixture
def subscription_api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    seed.execute(insert(user_table), [{"id": 1, "email": "one@subscription.test", "password_hash": "x"}, {"id": 2, "email": "two@subscription.test", "password_hash": "x"}])
    seed.execute(insert(organization_table), [
        {"id": 1, "name": "One", "slug": "subscription-one", "owner_user_id": 1, "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 2, "name": "Two", "slug": "subscription-two", "owner_user_id": 2, "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    seed.add_all([Plan(id=1, code="starter", name="Starter", seat_limit=1, is_active=True), Plan(id=2, code="inactive", name="Inactive", seat_limit=1, is_active=False)])
    seed.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current] = lambda: {"organization": {"id": 1}}
    monkeypatch.setattr(routes, "SessionLocal", factory)
    yield TestClient(app, raise_server_exceptions=False), factory, app
    app.dependency_overrides.clear()
    seed.close()
    engine.dispose()


def create_body(**overrides):
    body = {"organization_id": 2, "plan_id": 1, "billing_cycle": "monthly", "starts_at": NOW.isoformat(), "renews_at": (NOW + timedelta(days=30)).isoformat(), "external_reference": "api-sub"}
    body.update(overrides)
    return body


def create(client, **overrides):
    response = client.post("/commercial/subscriptions", json=create_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def fresh(factory, identifier):
    session = factory()
    try:
        subscription = session.get(Subscription, identifier)
        history = list(session.query(SubscriptionHistory).filter_by(subscription_id=identifier).all())
        return subscription, history
    finally:
        session.close()


def test_openapi_and_missing_or_invalid_authentication():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    assert "/commercial/subscriptions" in schema["paths"]
    assert "SubscriptionCreate" in schema["components"]["schemas"]
    assert "SubscriptionOut" in schema["components"]["schemas"]
    assert client.get("/commercial/subscriptions").status_code == 403
    assert client.get("/commercial/subscriptions", headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get("/commercial/subscriptions", headers={"Authorization": "invalid"}).status_code == 403


def test_list_is_organization_scoped_including_empty_result(subscription_api):
    client, factory, app = subscription_api
    ours = create(client)
    session = factory()
    session.add(Subscription(organization_id=2, plan_id=1, status="pending", billing_cycle="monthly", starts_at=NOW)); session.commit(); session.close()
    assert [row["id"] for row in client.get("/commercial/subscriptions").json()] == [ours["id"]]
    app.dependency_overrides[current] = lambda: {"organization": {"id": 999}}
    assert client.get("/commercial/subscriptions").json() == []


def test_retrieve_success_unknown_and_cross_organization_are_safe(subscription_api):
    client, factory, _ = subscription_api
    ours = create(client)
    session = factory()
    other = Subscription(organization_id=2, plan_id=1, status="pending", billing_cycle="monthly", starts_at=NOW, external_reference="secret")
    session.add(other); session.commit(); other_id = other.id; session.close()
    assert client.get(f"/commercial/subscriptions/{ours['id']}").json()["id"] == ours["id"]
    assert client.get("/commercial/subscriptions/9999").status_code == 404
    blocked = client.get(f"/commercial/subscriptions/{other_id}")
    assert blocked.status_code == 404 and "secret" not in blocked.text


def test_create_uses_authenticated_organization_and_records_history(subscription_api):
    client, factory, _ = subscription_api
    result = create(client)
    stored, history = fresh(factory, result["id"])
    assert result["organization_id"] == stored.organization_id == 1
    assert result["status"] == "pending" and result["version"] == 1
    assert [(record.event_type, record.new_status) for record in history] == [("created", "pending")]


@pytest.mark.parametrize("changes", [{"plan_id": 999}, {"plan_id": 2}, {"billing_cycle": "weekly"}, {"ends_at": (NOW - timedelta(days=1)).isoformat()}])
def test_create_rejects_invalid_plan_or_dates_without_partial_rows(subscription_api, changes):
    client, factory, _ = subscription_api
    response = client.post("/commercial/subscriptions", json=create_body(**changes))
    assert response.status_code == 409
    session = factory()
    assert session.query(Subscription).count() == 0 and session.query(SubscriptionHistory).count() == 0
    session.close()


def test_create_rejects_invalid_body_and_duplicate_current_subscription(subscription_api):
    client, _, _ = subscription_api
    assert client.post("/commercial/subscriptions", json={}).status_code == 422
    created = create(client)
    assert client.post(f"/commercial/subscriptions/{created['id']}/activate", json={}).status_code == 200
    assert client.post("/commercial/subscriptions", json=create_body(external_reference="second")).status_code == 409


def test_activation_persists_and_records_history(subscription_api):
    client, factory, _ = subscription_api
    created = create(client)
    response = client.post(f"/commercial/subscriptions/{created['id']}/activate", json={"renews_at": (NOW + timedelta(days=60)).isoformat()})
    assert response.status_code == 200 and response.json()["status"] == "active"
    stored, history = fresh(factory, created["id"])
    assert stored.status == "active" and stored.version == 2
    assert [record.event_type for record in history] == ["created", "activated"]


def test_activation_unknown_cross_org_and_repeated_transition_are_rejected(subscription_api):
    client, factory, _ = subscription_api
    created = create(client)
    assert client.post("/commercial/subscriptions/9999/activate", json={}).status_code == 404
    session = factory(); other = Subscription(organization_id=2, plan_id=1, status="pending", billing_cycle="monthly", starts_at=NOW); session.add(other); session.commit(); other_id = other.id; session.close()
    assert client.post(f"/commercial/subscriptions/{other_id}/activate", json={}).status_code == 404
    assert client.post(f"/commercial/subscriptions/{created['id']}/activate", json={}).status_code == 200
    assert client.post(f"/commercial/subscriptions/{created['id']}/activate", json={}).status_code == 409


def test_trial_creation_activation_expiry_and_history(subscription_api, monkeypatch):
    client, factory, _ = subscription_api
    trial_end = NOW + timedelta(days=7)
    trial = client.post("/commercial/subscriptions/trial", json={"organization_id": 2, "plan_id": 1, "billing_cycle": "monthly", "trial_ends_at": trial_end.isoformat()})
    assert trial.status_code == 201 and trial.json()["status"] == "trialing"
    identifier = trial.json()["id"]
    assert client.post(f"/commercial/subscriptions/{identifier}/activate-trial", json={}).status_code == 200
    stored, history = fresh(factory, identifier)
    assert stored.status == "active" and [item.event_type for item in history] == ["trial_started", "activated"]
    # A separate trial is expired under a deterministic service clock.
    session = factory(); expired = Subscription(organization_id=2, plan_id=1, status="trialing", billing_cycle="monthly", starts_at=NOW - timedelta(days=2), trial_ends_at=NOW - timedelta(days=1)); session.add(expired); session.commit(); expired_id = expired.id; session.close()
    class ClockedService(SubscriptionLifecycleService):
        def __init__(self, session): super().__init__(session, clock=lambda: NOW)
    monkeypatch.setattr(routes, "SubscriptionLifecycleService", ClockedService)
    app = client.app; app.dependency_overrides[current] = lambda: {"organization": {"id": 2}}
    assert client.post(f"/commercial/subscriptions/{expired_id}/expire-trial").status_code == 200
    stored, history = fresh(factory, expired_id)
    assert stored.status == "expired" and history[-1].event_type == "trial_ended"


def test_trial_invalid_period_and_cross_organization_lifecycle_are_rejected(subscription_api):
    client, factory, _ = subscription_api
    assert client.post("/commercial/subscriptions/trial", json={"plan_id": 1, "billing_cycle": "monthly", "trial_ends_at": datetime(2000, 1, 1, tzinfo=timezone.utc).isoformat()}).status_code == 409
    session = factory(); other = Subscription(organization_id=2, plan_id=1, status="trialing", billing_cycle="monthly", starts_at=NOW, trial_ends_at=NOW + timedelta(days=1)); session.add(other); session.commit(); identifier = other.id; session.close()
    assert client.post(f"/commercial/subscriptions/{identifier}/activate-trial", json={}).status_code == 404
    assert client.post(f"/commercial/subscriptions/{identifier}/expire-trial").status_code == 404
    future_end = datetime.now(timezone.utc) + timedelta(days=1)
    session = factory(); current_trial = Subscription(organization_id=1, plan_id=1, status="trialing", billing_cycle="monthly", starts_at=NOW, trial_ends_at=future_end); session.add(current_trial); session.commit(); current_id = current_trial.id; session.close()
    assert client.post(f"/commercial/subscriptions/{current_id}/expire-trial").status_code == 409


def test_history_is_owned_ordered_and_not_exposed_cross_organization(subscription_api):
    client, factory, _ = subscription_api
    created = create(client)
    assert client.post(f"/commercial/subscriptions/{created['id']}/activate", json={}).status_code == 200
    response = client.get(f"/commercial/subscriptions/{created['id']}/history")
    assert response.status_code == 200 and [record["event_type"] for record in response.json()] == ["created", "activated"]
    session = factory(); other = Subscription(organization_id=2, plan_id=1, status="pending", billing_cycle="monthly", starts_at=NOW); session.add(other); session.commit(); identifier = other.id; session.close()
    assert client.get(f"/commercial/subscriptions/{identifier}/history").status_code == 404


@pytest.mark.parametrize("kind", ["create", "activate", "start_trial", "trial", "expire"])
def test_commit_failure_rolls_back_subscription_and_history(subscription_api, monkeypatch, kind):
    client, factory, _ = subscription_api
    identifier = None
    if kind == "activate": identifier = create(client)["id"]
    if kind == "trial":
        session = factory(); target = Subscription(organization_id=1, plan_id=1, status="trialing", billing_cycle="monthly", starts_at=NOW, trial_ends_at=NOW + timedelta(days=1)); session.add(target); session.commit(); identifier = target.id; session.close()
    if kind == "expire":
        session = factory(); target = Subscription(organization_id=1, plan_id=1, status="trialing", billing_cycle="monthly", starts_at=NOW - timedelta(days=2), trial_ends_at=NOW - timedelta(days=1)); session.add(target); session.commit(); identifier = target.id; session.close()
        class ClockedService(SubscriptionLifecycleService):
            def __init__(self, session): super().__init__(session, clock=lambda: NOW)
        monkeypatch.setattr(routes, "SubscriptionLifecycleService", ClockedService)
    class BrokenSession:
        def __init__(self): self.inner = factory(); self.rolled = False
        def __getattr__(self, name): return getattr(self.inner, name)
        def commit(self): raise RuntimeError("forced commit failure")
        def rollback(self): self.rolled = True; self.inner.rollback()
        def close(self): self.inner.close()
    broken = BrokenSession(); monkeypatch.setattr(routes, "SessionLocal", lambda: broken)
    if kind == "create": response = client.post("/commercial/subscriptions", json=create_body())
    elif kind == "start_trial": response = client.post("/commercial/subscriptions/trial", json={"plan_id": 1, "billing_cycle": "monthly", "trial_ends_at": (NOW + timedelta(days=7)).isoformat()})
    elif kind == "activate": response = client.post(f"/commercial/subscriptions/{identifier}/activate", json={})
    elif kind == "trial": response = client.post(f"/commercial/subscriptions/{identifier}/activate-trial", json={})
    else: response = client.post(f"/commercial/subscriptions/{identifier}/expire-trial")
    assert response.status_code >= 500 and broken.rolled
    if kind in {"create", "start_trial"}:
        session = factory(); assert session.query(Subscription).count() == 0 and session.query(SubscriptionHistory).count() == 0; session.close()
    else:
        stored, history = fresh(factory, identifier)
        assert stored.status in {"pending", "trialing"} and len(history) == (1 if kind == "activate" else 0)


@pytest.mark.parametrize("initial,route,expected,event", [
    ("active", "suspend", "paused", "paused"),
    ("paused", "resume", "active", "resumed"),
    ("trialing", "cancel", "cancelled", "cancelled"),
    ("active", "cancel", "cancelled", "cancelled"),
    ("paused", "cancel", "cancelled", "cancelled"),
    ("active", "expire", "expired", "expired"),
])
def test_new_lifecycle_routes_persist_one_history_record(subscription_api, initial, route, expected, event):
    client, factory, _ = subscription_api
    ends_at = NOW - timedelta(days=1) if route == "expire" else None
    session = factory(); subscription = Subscription(organization_id=1, plan_id=1, status=initial, billing_cycle="monthly", starts_at=NOW - timedelta(days=2), ends_at=ends_at); session.add(subscription); session.commit(); identifier = subscription.id; session.close()
    response = client.post(f"/commercial/subscriptions/{identifier}/{route}")
    assert response.status_code == 200 and response.json()["status"] == expected
    stored, history = fresh(factory, identifier)
    assert stored.status == expected and [item.event_type for item in history] == [event]


@pytest.mark.parametrize("initial,route", [("pending", "suspend"), ("active", "resume"), ("paused", "expire"), ("trialing", "expire"), ("cancelled", "resume"), ("expired", "cancel"), ("active", "expire")])
def test_new_lifecycle_routes_reject_invalid_transition_without_history(subscription_api, initial, route):
    client, factory, _ = subscription_api
    ends_at = datetime.now(timezone.utc) + timedelta(days=1) if initial == "active" and route == "expire" else None
    session = factory(); subscription = Subscription(organization_id=1, plan_id=1, status=initial, billing_cycle="monthly", starts_at=NOW, ends_at=ends_at); session.add(subscription); session.commit(); identifier = subscription.id; session.close()
    assert client.post(f"/commercial/subscriptions/{identifier}/{route}").status_code == 409
    stored, history = fresh(factory, identifier)
    assert stored.status == initial and history == []


@pytest.mark.parametrize("route", ["suspend", "resume", "cancel", "expire"])
def test_new_lifecycle_routes_hide_cross_organization_resources(subscription_api, route):
    client, factory, _ = subscription_api
    session = factory(); subscription = Subscription(organization_id=2, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW - timedelta(days=2), ends_at=NOW - timedelta(days=1)); session.add(subscription); session.commit(); identifier = subscription.id; session.close()
    assert client.post(f"/commercial/subscriptions/{identifier}/{route}").status_code == 404
    stored, history = fresh(factory, identifier)
    assert stored.status == "active" and history == []


def test_openapi_registers_new_lifecycle_routes():
    app = FastAPI(); app.include_router(router); paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert all(f"/commercial/subscriptions/{{subscription_id}}/{route}" in paths for route in ("suspend", "resume", "cancel", "expire"))
