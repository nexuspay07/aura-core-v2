"""Integration coverage for the supported Refund HTTP contract."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

import app.api.refund_routes as routes
from app.api.refund_routes import current, router
from app.commercial.models import BillingAccount, Invoice, PaymentAttempt, Plan, Refund, Subscription
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def refund_api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    seed.execute(insert(user_table), [{"id": 1, "email": "one@example.test", "password_hash": "x"}, {"id": 2, "email": "two@example.test", "password_hash": "x"}])
    seed.execute(insert(organization_table), [
        {"id": 1, "name": "One", "slug": "refund-one", "owner_user_id": 1, "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 2, "name": "Two", "slug": "refund-two", "owner_user_id": 2, "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    plan = Plan(id=1, code="refund-api", name="Refund API", seat_limit=1)
    seed.add(plan)
    for organization_id in (1, 2):
        seed.add(BillingAccount(id=organization_id, organization_id=organization_id, billing_email=f"{organization_id}@example.test", billing_name=f"Org {organization_id}", country_code="CA", currency="CAD"))
        seed.add(Subscription(id=organization_id, organization_id=organization_id, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW))
        invoice = Invoice(id=organization_id, organization_id=organization_id, billing_account_id=organization_id, subscription_id=organization_id, invoice_number=f"REF-INV-{organization_id}", status="open", currency="CAD", period_start=NOW, period_end=datetime(2026, 2, 1, tzinfo=timezone.utc), subtotal_amount=Decimal("10"), tax_amount=0, discount_amount=0, total_amount=Decimal("10"), amount_due=Decimal("10"), amount_paid=0)
        seed.add(invoice)
        seed.add(PaymentAttempt(id=organization_id, invoice_id=organization_id, attempt_number=1, provider="fake", idempotency_key=f"attempt-{organization_id}", status="succeeded", amount=Decimal("10"), currency="CAD", requested_at=NOW, succeeded_at=NOW))
    seed.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current] = lambda: {"organization": {"id": 1}}
    monkeypatch.setattr(routes, "SessionLocal", factory)
    yield TestClient(app, raise_server_exceptions=False), factory, app
    app.dependency_overrides.clear()
    seed.close()
    engine.dispose()


def body(number="REF-1", key="refund-key-1", **overrides):
    value = {"organization_id": 2, "invoice_id": 1, "payment_attempt_id": 1, "amount": "4.0000", "currency": "CAD", "idempotency_key": key, "provider": "fake", "refund_number": number}
    value.update(overrides)
    return value


def create(client, number="REF-1", key="refund-key-1", **overrides):
    response = client.post("/commercial/refunds", json=body(number, key, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


def fresh(factory, refund_id):
    session = factory()
    try:
        return session.get(Refund, refund_id)
    finally:
        session.close()


def test_openapi_and_missing_authentication():
    app = FastAPI()
    app.include_router(router)
    schema = TestClient(app).get("/openapi.json").json()
    assert "/commercial/refunds" in schema["paths"]
    assert "RefundCreate" in schema["components"]["schemas"]
    assert "RefundOut" in schema["components"]["schemas"]
    assert TestClient(app).get("/commercial/refunds").status_code == 403


def test_invalid_token_rejected_before_protected_route_execution():
    app = FastAPI()
    app.include_router(router)
    assert TestClient(app).get("/commercial/refunds", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_list_is_organization_scoped_and_empty_for_another_org(refund_api):
    client, factory, app = refund_api
    ours = create(client)
    session = factory()
    session.add(Refund(organization_id=2, invoice_id=2, payment_attempt_id=2, refund_number="REF-OTHER", status="pending", amount=1, currency="CAD", idempotency_key="other", provider="fake", requested_at=NOW))
    session.commit(); session.close()
    response = client.get("/commercial/refunds")
    assert response.status_code == 200 and [item["id"] for item in response.json()] == [ours["id"]]
    app.dependency_overrides[current] = lambda: {"organization": {"id": 2}}
    assert [item["refund_number"] for item in client.get("/commercial/refunds").json()] == ["REF-OTHER"]
    app.dependency_overrides[current] = lambda: {"organization": {"id": 999}}
    assert client.get("/commercial/refunds").json() == []


def test_retrieval_success_unknown_and_cross_organization_are_safe(refund_api):
    client, factory, _ = refund_api
    ours = create(client)
    session = factory()
    other = Refund(organization_id=2, invoice_id=2, payment_attempt_id=2, refund_number="REF-OTHER", status="pending", amount=1, currency="CAD", idempotency_key="other", provider="fake", requested_at=NOW)
    session.add(other); session.commit(); other_id = other.id; session.close()
    assert client.get(f"/commercial/refunds/{ours['id']}").json()["id"] == ours["id"]
    assert client.get("/commercial/refunds/9999").status_code == 404
    blocked = client.get(f"/commercial/refunds/{other_id}")
    assert blocked.status_code == 404 and "REF-OTHER" not in blocked.text


def test_create_uses_authenticated_organization_and_persists_in_fresh_session(refund_api):
    client, factory, _ = refund_api
    result = create(client)
    stored = fresh(factory, result["id"])
    assert result["organization_id"] == 1 and stored.organization_id == 1
    assert stored.amount == Decimal("4.0000") and result["status"] == "pending"


@pytest.mark.parametrize("changes", [{"amount": "0"}, {"amount": "-1"}, {"amount": "11"}, {"invoice_id": 999}, {"payment_attempt_id": 999}, {"invoice_id": 2, "payment_attempt_id": 2}])
def test_create_rejects_invalid_financial_or_relationship_requests(refund_api, changes):
    client, factory, _ = refund_api
    response = client.post("/commercial/refunds", json=body(**changes))
    assert response.status_code == 409
    session = factory()
    assert session.query(Refund).count() == 0
    session.close()


def test_create_rejects_invalid_body_and_duplicate_idempotency(refund_api):
    client, _, _ = refund_api
    assert client.post("/commercial/refunds", json={}).status_code == 422
    first = create(client)
    duplicate = client.post("/commercial/refunds", json=body("REF-2", "refund-key-1", amount="5"))
    assert duplicate.status_code == 409
    assert client.get(f"/commercial/refunds/{first['id']}").status_code == 200


@pytest.mark.parametrize("endpoint, expected_status, extra", [
    ("processing", "processing", {"provider_reference": "provider-ref"}),
    ("succeeded", "succeeded", {"provider_reference": "provider-ref"}),
    ("failed", "failed", {"failure_code": "declined", "failure_message": "Declined"}),
    ("cancel", "cancelled", {}),
])
def test_supported_lifecycle_actions_persist(refund_api, endpoint, expected_status, extra):
    client, factory, _ = refund_api
    result = create(client)
    response = client.post(f"/commercial/refunds/{result['id']}/{endpoint}", json={"expected_version": 1, **extra})
    assert response.status_code == 200, response.text
    stored = fresh(factory, result["id"])
    assert stored.status == expected_status and stored.version == 2
    if endpoint == "processing": assert stored.provider_reference == "provider-ref"
    if endpoint == "failed": assert stored.failure_code == "declined"


@pytest.mark.parametrize("endpoint", ["processing", "succeeded", "failed", "cancel"])
def test_lifecycle_unknown_cross_org_and_invalid_transition_are_rejected(refund_api, endpoint):
    client, factory, _ = refund_api
    result = create(client)
    assert client.post(f"/commercial/refunds/9999/{endpoint}", json={"expected_version": 1}).status_code == 404
    session = factory()
    other = Refund(organization_id=2, invoice_id=2, payment_attempt_id=2, refund_number="REF-OTHER", status="pending", amount=1, currency="CAD", idempotency_key="other", provider="fake", requested_at=NOW)
    session.add(other); session.commit(); other_id = other.id; session.close()
    assert client.post(f"/commercial/refunds/{other_id}/{endpoint}", json={"expected_version": 1}).status_code == 404
    first = client.post(f"/commercial/refunds/{result['id']}/{endpoint}", json={"expected_version": 1})
    assert first.status_code == 200
    assert client.post(f"/commercial/refunds/{result['id']}/{endpoint}", json={"expected_version": 2}).status_code == 409


def test_partial_refunds_reserve_payment_attempt_amount_without_mutating_invoice_or_attempt_state(refund_api):
    client, factory, _ = refund_api
    first = create(client, "REF-1", "key-1", amount="4")
    second = create(client, "REF-2", "key-2", amount="6")
    assert first["status"] == second["status"] == "pending"
    assert client.post("/commercial/refunds", json=body("REF-3", "key-3", amount="0.0001")).status_code == 409
    session = factory()
    attempt = session.get(PaymentAttempt, 1); invoice = session.get(Invoice, 1)
    assert attempt.status == "succeeded" and invoice.amount_due == Decimal("10.0000")
    session.close()


@pytest.mark.parametrize("endpoint", ["processing", "succeeded", "failed", "cancel"])
def test_commit_failure_rolls_back_lifecycle_change(refund_api, monkeypatch, endpoint):
    client, factory, _ = refund_api
    result = create(client)
    class BrokenSession:
        def __init__(self): self.inner = factory(); self.rolled = False
        def __getattr__(self, name): return getattr(self.inner, name)
        def commit(self): raise RuntimeError("forced commit failure")
        def rollback(self): self.rolled = True; self.inner.rollback()
        def close(self): self.inner.close()
    broken = BrokenSession()
    monkeypatch.setattr(routes, "SessionLocal", lambda: broken)
    response = client.post(f"/commercial/refunds/{result['id']}/{endpoint}", json={"expected_version": 1})
    assert response.status_code >= 500 and broken.rolled
    stored = fresh(factory, result["id"])
    assert stored.status == "pending" and stored.version == 1


def test_commit_failure_rolls_back_create_without_financial_mutation(refund_api, monkeypatch):
    client, factory, _ = refund_api
    class BrokenSession:
        def __init__(self): self.inner = factory(); self.rolled = False
        def __getattr__(self, name): return getattr(self.inner, name)
        def commit(self): raise RuntimeError("forced commit failure")
        def rollback(self): self.rolled = True; self.inner.rollback()
        def close(self): self.inner.close()
    broken = BrokenSession(); monkeypatch.setattr(routes, "SessionLocal", lambda: broken)
    response = client.post("/commercial/refunds", json=body())
    assert response.status_code >= 500 and broken.rolled
    session = factory()
    assert session.query(Refund).count() == 0 and session.get(PaymentAttempt, 1).version == 1
    session.close()
