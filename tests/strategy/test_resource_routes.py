import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.orm import sessionmaker

import app.db.schema  # noqa: F401
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.strategy_idempotency_table import strategy_create_idempotency_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.intelligence_v2.model_provider import ProviderTimeoutError
from app.strategy.application import StrategyApplicationService
from app.strategy.contracts import StrategyPhase, StrategyResult, SuccessMeasure
from app.strategy.persistence import StrategyRepository
from app.strategy.idempotency import (
    StrategyCreateIdempotencyRepository,
    StrategyIdempotencyCompletionError,
)
from app.strategy import resource_routes, routes


def payload(**changes):
    value = {
        "title": "  Reliability   strategy  ",
        "objective": "Retain key customers",
        "chosen_direction": "Improve reliability",
        "constraints": ["Protect service continuity."],
        "resources": [{"name": "Platform team", "description": "Owns reliability."}],
        "assumptions": ["Customers value stability."],
        "risks": [{"risk": "Delivery may slip.", "mitigation": "Use staged reviews."}],
        "uncertainties": ["Future demand remains uncertain."],
        "time_horizon": "Next planning cycle",
        "change_conditions": ["Reliability does not improve."],
    }
    value.update(changes)
    return value


def generated(source):
    return StrategyResult(
        scope=source.scope,
        objective=source.objective,
        chosen_direction=source.chosen_direction,
        approach="Stabilize dependencies before expanding.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        success_measures=(SuccessMeasure("Reliability improves."),),
        change_conditions=source.change_conditions,
        confidence=source.confidence,
        confidence_rationale=source.confidence_rationale,
        constraints=source.constraints,
        assumptions=source.assumptions,
        resources=source.resources,
        risks=source.risks,
        uncertainties=source.uncertainties,
        time_horizon=source.time_horizon,
    )


class RecordingCapability:
    def __init__(self, sessions, errors=None):
        self.sessions = sessions
        self.errors = list(errors or [])
        self.calls = 0

    def generate(self, source, *, before_provider_attempt=None):
        self.calls += 1
        if before_provider_attempt:
            before_provider_attempt()
            assert self.sessions and not self.sessions[-1].in_transaction()
        if self.errors:
            error = self.errors.pop(0)
            if error:
                raise error
        return generated(source)


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'resources.db'}")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    seed = factory()
    seed.execute(insert(user_table), [
        {"id": 1, "email": "one@resources.test", "password_hash": "x"},
        {"id": 2, "email": "two@resources.test", "password_hash": "x"},
    ])
    seed.execute(insert(organization_table), [
        {"id": 10, "name": "One", "slug": "one-resources", "owner_user_id": 1, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 20, "name": "Two", "slug": "two-resources", "owner_user_id": 2, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    seed.execute(insert(workspace_table), [
        {"id": 11, "organization_id": 10, "created_by_user_id": 1, "name": "One", "slug": "one-resources-workspace", "workspace_type": "business", "is_active": True},
        {"id": 12, "organization_id": 10, "created_by_user_id": 1, "name": "Other", "slug": "other-resources-workspace", "workspace_type": "business", "is_active": True},
        {"id": 21, "organization_id": 20, "created_by_user_id": 2, "name": "Two", "slug": "two-resources-workspace", "workspace_type": "business", "is_active": True},
    ])
    seed.commit(); seed.close()

    sessions = []

    def session_factory():
        session = factory()
        sessions.append(session)
        return session

    identity = {"value": {"user": {"id": 1}, "organization": None, "workspace": None}}

    async def current(_):
        return identity["value"]

    capability = RecordingCapability(sessions)
    application = StrategyApplicationService(capability, StrategyRepository())
    monkeypatch.setattr(routes, "get_current_user_from_token", current)
    monkeypatch.setattr(resource_routes, "SessionLocal", session_factory)
    monkeypatch.setattr(resource_routes, "strategy_application_service", application)
    app = FastAPI()
    app.include_router(routes.router)
    app.include_router(resource_routes.router)
    client = TestClient(app, raise_server_exceptions=False)
    yield client, factory, capability, identity, sessions, application
    engine.dispose()


HEADERS = {"Authorization": "Bearer token", "Idempotency-Key": "opaque-create-key"}


def test_persistent_create_requires_auth_and_idempotency_key(api):
    client, *_ = api
    assert client.post("/strategy-resources", json=payload()).status_code == 403
    assert client.post("/strategy-resources", headers={"Authorization": "Bearer token"}, json=payload()).status_code == 422
    assert client.post("/strategy-resources", headers={**HEADERS, "Idempotency-Key": "x" * 256}, json=payload()).status_code == 422
    assert client.post("/strategy-resources", headers={**HEADERS, "Idempotency-Key": "   "}, json=payload()).status_code == 422


def test_personal_create_persists_direct_resource_and_safe_response(api):
    client, factory, capability, *_ = api
    response = client.post("/strategy-resources", headers=HEADERS, json=payload())
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Reliability strategy"
    assert len(body["public_id"]) == 36
    assert body["current_revision"] == body["resource_version"] == 1
    assert body["archived"] is False and body["strategy"]["source_decision_id"] is None
    assert capability.calls == 1
    for forbidden in ("id", "owner_user_id", "created_by_user_id", "idempotency_key", "request_fingerprint", "claim_token", "canonical_result_json", "lock_version"):
        assert forbidden not in body
    db = factory()
    resource = db.execute(select(strategy_resource_table)).mappings().one()
    revision = db.execute(select(strategy_revision_table)).mappings().one()
    claim = db.execute(select(strategy_create_idempotency_table)).mappings().one()
    assert resource["owner_user_id"] == 1 and resource["title"] == "Reliability strategy"
    assert revision["origin_type"] == "direct" and revision["source_decision_id"] is None
    assert claim["status"] == "completed" and claim["strategy_resource_id"] == resource["id"]
    db.close()


def test_completed_replay_conflict_and_active_duplicate_do_not_call_provider(api):
    client, factory, capability, *_ = api
    first = client.post("/strategy-resources", headers=HEADERS, json=payload())
    replay = client.post("/strategy-resources", headers=HEADERS, json=payload())
    conflict = client.post("/strategy-resources", headers=HEADERS, json=payload(objective="Different"))
    assert replay.status_code == 201 and replay.json()["public_id"] == first.json()["public_id"]
    assert conflict.status_code == 409 and capability.calls == 1

    active_headers = {**HEADERS, "Idempotency-Key": "active"}
    db = factory()
    source = routes.to_strategy_input(resource_routes.PersistentStrategyCreateRequest(**payload()), routes.authorized_scope({"user": {"id": 1}}))
    fingerprint = __import__("app.strategy.idempotency", fromlist=["strategy_create_request_fingerprint"]).strategy_create_request_fingerprint(title=payload()["title"], strategy_input=source)
    application = resource_routes.strategy_application_service
    application.idempotency_repository.claim(db, idempotency_key="active", request_fingerprint=fingerprint, actor_user_id=1, scope=source.scope)
    db.commit(); db.close()
    active = client.post("/strategy-resources", headers=active_headers, json=payload())
    assert active.status_code == 409
    assert active.json()["detail"]["code"] == "strategy_creation_in_progress"
    assert capability.calls == 1


def test_key_is_scoped_by_actor_and_authorized_workspace(api):
    client, _, capability, identity, *_ = api
    one = client.post("/strategy-resources", headers=HEADERS, json=payload())
    identity["value"] = {"user": {"id": 2}, "organization": None, "workspace": None}
    two = client.post("/strategy-resources", headers=HEADERS, json=payload())
    identity["value"] = {"user": {"id": 1}, "organization": {"id": 10}, "workspace": {"id": 11}}
    workspace = client.post("/strategy-resources", headers=HEADERS, json=payload())
    assert {one.status_code, two.status_code, workspace.status_code} == {201}
    assert len({one.json()["public_id"], two.json()["public_id"], workspace.json()["public_id"]}) == 3
    assert capability.calls == 3


@pytest.mark.parametrize("field", [
    "public_id", "revision", "lock_version", "owner_user_id", "created_by_user_id",
    "actor_user_id", "organization_id", "workspace_id", "origin_type", "source_decision_id",
    "confidence", "confidence_rationale", "provider", "model", "canonical_result_json",
])
def test_create_rejects_spoofed_or_internal_fields(api, field):
    client, *_ = api
    assert client.post("/strategy-resources", headers=HEADERS, json=payload(**{field: 1})).status_code == 422


def test_generation_failure_creates_nothing_and_can_retry(api):
    client, factory, capability, *_ = api
    capability.errors[:] = [ProviderTimeoutError("private timeout"), None]
    failed = client.post("/strategy-resources", headers=HEADERS, json=payload())
    assert failed.status_code == 504 and "private" not in failed.text
    db = factory()
    assert db.execute(select(strategy_resource_table)).all() == []
    assert db.execute(select(strategy_create_idempotency_table)).mappings().one()["status"] == "in_progress"
    db.close()
    retried = client.post("/strategy-resources", headers=HEADERS, json=payload())
    assert retried.status_code == 201 and capability.calls == 2


def test_forced_completion_failure_rolls_back_resource_and_revision(api, monkeypatch):
    client, factory, capability, *_ = api

    class FailAfterCompletion(StrategyCreateIdempotencyRepository):
        def complete_with_strategy(self, db, **values):
            super().complete_with_strategy(db, **values)
            raise StrategyIdempotencyCompletionError("forced private failure")

    monkeypatch.setattr(
        resource_routes,
        "strategy_application_service",
        StrategyApplicationService(capability, StrategyRepository(), FailAfterCompletion()),
    )
    response = client.post("/strategy-resources", headers=HEADERS, json=payload())
    assert response.status_code == 409 and "private" not in response.text
    db = factory()
    assert db.execute(select(strategy_resource_table)).all() == []
    assert db.execute(select(strategy_revision_table)).all() == []
    claim = db.execute(select(strategy_create_idempotency_table)).mappings().one()
    assert claim["status"] == "in_progress" and claim["strategy_resource_id"] is None
    db.close()


def test_list_get_archive_are_tenant_safe_lightweight_and_provider_free(api):
    client, factory, capability, identity, *_ = api
    created = client.post("/strategy-resources", headers=HEADERS, json=payload()).json()
    public_id = created["public_id"]
    calls = capability.calls
    listed = client.get("/strategy-resources", headers={"Authorization": "Bearer token"})
    assert listed.status_code == 200 and len(listed.json()["items"]) == 1
    item = listed.json()["items"][0]
    assert "strategy" not in item and "id" not in item and item["public_id"] == public_id
    assert client.get("/strategy-resources?limit=0", headers={"Authorization": "Bearer token"}).status_code == 422
    assert client.get("/strategy-resources?limit=101", headers={"Authorization": "Bearer token"}).status_code == 422
    fetched = client.get(f"/strategy-resources/{public_id}", headers={"Authorization": "Bearer token"})
    assert fetched.status_code == 200 and fetched.json()["strategy"]["approach"]

    identity["value"] = {"user": {"id": 2}, "organization": None, "workspace": None}
    assert client.get(f"/strategy-resources/{public_id}", headers={"Authorization": "Bearer token"}).status_code == 404
    assert client.post(f"/strategy-resources/{public_id}/archive", headers={"Authorization": "Bearer token"}, json={"resource_version": 1}).status_code == 404
    identity["value"] = {"user": {"id": 1}, "organization": None, "workspace": None}

    stale = client.post(f"/strategy-resources/{public_id}/archive", headers={"Authorization": "Bearer token"}, json={})
    assert stale.status_code == 422
    archived = client.post(f"/strategy-resources/{public_id}/archive", headers={"Authorization": "Bearer token"}, json={"resource_version": 1})
    assert archived.status_code == 200
    assert archived.json()["archived"] is True and archived.json()["resource_version"] == 2
    repeated = client.post(f"/strategy-resources/{public_id}/archive", headers={"Authorization": "Bearer token"}, json={"resource_version": 1})
    assert repeated.status_code == 200 and repeated.json()["resource_version"] == 2
    assert client.get("/strategy-resources", headers={"Authorization": "Bearer token"}).json()["items"] == []
    db = factory()
    assert len(db.execute(select(strategy_revision_table)).all()) == 1
    db.close()
    assert capability.calls == calls


def test_stale_archive_version_returns_conflict_without_revision_mutation(api):
    client, factory, capability, *_ = api
    created = client.post("/strategy-resources", headers=HEADERS, json=payload()).json()
    db = factory()
    db.execute(update(strategy_resource_table).where(
        strategy_resource_table.c.public_id == created["public_id"]
    ).values(lock_version=2))
    db.commit(); db.close()
    response = client.post(
        f"/strategy-resources/{created['public_id']}/archive",
        headers={"Authorization": "Bearer token"},
        json={"resource_version": 1},
    )
    assert response.status_code == 409
    db = factory()
    assert len(db.execute(select(strategy_revision_table)).all()) == 1
    assert db.execute(select(strategy_resource_table.c.archived_at)).scalar_one() is None
    db.close()
    assert capability.calls == 1


def test_workspace_list_get_and_archive_use_exact_active_scope(api):
    client, _, capability, identity, *_ = api
    identity["value"] = {"user": {"id": 1}, "organization": {"id": 10}, "workspace": {"id": 11}}
    created = client.post("/strategy-resources", headers=HEADERS, json=payload()).json()
    identity["value"] = {"user": {"id": 1}, "organization": {"id": 10}, "workspace": {"id": 12}}
    assert client.get("/strategy-resources", headers={"Authorization": "Bearer token"}).json()["items"] == []
    assert client.get(f"/strategy-resources/{created['public_id']}", headers={"Authorization": "Bearer token"}).status_code == 404
    identity["value"] = {"user": {"id": 1}, "organization": {"id": 10}, "workspace": {"id": 11}}
    assert client.get(f"/strategy-resources/{created['public_id']}", headers={"Authorization": "Bearer token"}).status_code == 200
    assert client.post(f"/strategy-resources/{created['public_id']}/archive", headers={"Authorization": "Bearer token"}, json={"resource_version": 1}).status_code == 200
    assert capability.calls == 1


def test_existing_ephemeral_route_remains_non_persistent_and_header_free(api, monkeypatch):
    client, factory, _, identity, *_ = api
    ephemeral = RecordingCapability([])
    monkeypatch.setattr(routes, "strategy_capability", ephemeral)
    response = client.post("/strategies", headers={"Authorization": "Bearer token"}, json={key: value for key, value in payload().items() if key != "title"})
    assert response.status_code == 200 and ephemeral.calls == 1
    db = factory()
    assert db.execute(select(strategy_resource_table)).all() == []
    assert db.execute(select(strategy_create_idempotency_table)).all() == []
    db.close()
