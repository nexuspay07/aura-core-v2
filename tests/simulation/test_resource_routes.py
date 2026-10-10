import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.schema  # noqa: F401
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.simulation_resource_table import simulation_resource_table, simulation_run_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.simulation import ScenarioSeverity, ScenarioSource, SimulationScenario, UserSimulationAssumption
from app.simulation.application import (
    SimulationApplicationGenerationError,
    SimulationApplicationPersistenceError,
    SimulationApplicationService,
)
from app.simulation import resource_routes
from app.strategy.contracts import StrategyScope
from app.strategy.routes import current_identity
from tests.simulation.test_application import Orchestrator
from tests.simulation.test_persistence import persisted_strategy


PERSONAL = {"user": {"id": 1}, "organization": {"account_type": "personal"}}
WORKSPACE = {"user": {"id": 1}, "organization": {"id": 10, "account_type": "business"}, "workspace": {"id": 11}}
HEADERS = {"Authorization": "Bearer token", "Idempotency-Key": "simulation-key"}


def payload(**changes):
    value = {
        "title": "Reliability stress test",
        "scenarios": [{
            "key": "adverse", "name": "Adverse",
            "description": "Demand rises before capacity improves.",
            "changed_conditions": ["Demand exceeds capacity."],
            "qualitative_severity": "HIGH",
        }],
        "user_assumptions": [{"text": "Staffing remains fixed.", "scenario_key": "adverse"}],
    }
    value.update(changes)
    return value


@pytest.fixture
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    db.execute(insert(user_table), [
        {"id": 1, "email": "one@test", "password_hash": "x"},
        {"id": 2, "email": "two@test", "password_hash": "x"},
    ])
    db.execute(insert(organization_table), [
        {"id": 10, "name": "One", "slug": "sim-api-one", "owner_user_id": 1, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 20, "name": "Two", "slug": "sim-api-two", "owner_user_id": 2, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    db.execute(insert(workspace_table), [
        {"id": 11, "organization_id": 10, "created_by_user_id": 1, "name": "One", "slug": "sim-api-w1", "workspace_type": "business", "is_active": True},
        {"id": 12, "organization_id": 10, "created_by_user_id": 1, "name": "Other", "slug": "sim-api-w2", "workspace_type": "business", "is_active": True},
        {"id": 21, "organization_id": 20, "created_by_user_id": 2, "name": "Two", "slug": "sim-api-w3", "workspace_type": "business", "is_active": True},
    ])
    db.commit()
    runner = Orchestrator()
    monkeypatch.setattr(resource_routes, "SessionLocal", factory)
    monkeypatch.setattr(resource_routes, "simulation_application_service", SimulationApplicationService(orchestrator=runner))
    app = FastAPI()
    app.include_router(resource_routes.router)
    identity = {"value": PERSONAL}
    app.dependency_overrides[current_identity] = lambda: identity["value"]
    yield TestClient(app, raise_server_exceptions=False), db, runner, identity, app
    db.close()
    engine.dispose()


def create(client, strategy, **kwargs):
    return client.post(
        f"/strategy-resources/{strategy.public_id}/simulations",
        headers=kwargs.pop("headers", HEADERS), json=kwargs.pop("body", payload()),
    )


def test_authenticated_personal_create_and_replay_are_safe_and_typed(api):
    client, db, runner, _, _ = api
    strategy = persisted_strategy(db); db.commit()
    first = create(client, strategy)
    replay = create(client, strategy)
    assert first.status_code == replay.status_code == 201
    body = first.json()
    assert replay.json()["simulation_public_id"] == body["simulation_public_id"]
    assert body["source_strategy_public_id"] == strategy.public_id
    assert body["source_strategy_revision"] == 1 and body["run_number"] == 1
    assert body["result"]["confidence"] == "MODERATE"
    assert any(item["code"] == "not_calibrated" for item in body["result"]["limitations"])
    assert body["result"]["scenario_results"][0]["elements_under_stress"][0]["provenance"] == "MODEL_GENERATED"
    serialized = json.dumps(body).casefold()
    for forbidden in ("owner_user_id", "organization_id", "workspace_id", "claim_token", "lock_version", "probability", "prompt", "raw_provider"):
        assert forbidden not in serialized
    assert len(runner.calls) == 1
    assert len(db.execute(select(simulation_resource_table)).all()) == 1
    assert len(db.execute(select(simulation_run_table)).all()) == 1


def test_workspace_create_returns_decision_snapshot_and_exact_scope(api):
    client, db, runner, identity, _ = api
    identity["value"] = WORKSPACE
    strategy = persisted_strategy(db, StrategyScope(1, 10, 11), decision_snapshot=True); db.commit()
    response = create(client, strategy)
    assert response.status_code == 201
    assert response.json()["source_decision_snapshot_public_id"] == "00000000-0000-4000-8000-000000000101"
    row = db.execute(select(simulation_resource_table)).mappings().one()
    assert row["owner_user_id"] is None and (row["organization_id"], row["workspace_id"]) == (10, 11)
    assert len(runner.calls) == 1


@pytest.mark.parametrize("headers", [
    {"Authorization": "Bearer token"},
    {"Authorization": "Bearer token", "Idempotency-Key": "   "},
    {"Authorization": "Bearer token", "Idempotency-Key": "x" * 256},
])
def test_missing_or_malformed_idempotency_key_is_rejected(api, headers):
    client, db, runner, _, _ = api
    strategy = persisted_strategy(db); db.commit()
    assert create(client, strategy, headers=headers).status_code == 422
    assert runner.calls == []


@pytest.mark.parametrize("body", [
    payload(scenarios=[]),
    payload(scenarios=[{"key": "BAD KEY", "name": "A", "description": "B", "changed_conditions": ["C"]}]),
    payload(owner_user_id=1),
    payload(strategy_revision=9),
    payload(provider="openai"),
    payload(scenarios=[{**payload()["scenarios"][0], "source": "SYSTEM_DERIVED"}]),
    payload(user_assumptions=[{"text": "x", "provenance": "MODEL_GENERATED"}]),
])
def test_request_rejects_malformed_or_authority_fields_before_provider(api, body):
    client, db, runner, _, _ = api
    strategy = persisted_strategy(db); db.commit()
    assert create(client, strategy, body=body).status_code == 422
    assert runner.calls == []


def test_malformed_uuid_inaccessible_strategy_and_same_key_conflict_are_safe(api):
    client, db, runner, _, _ = api
    strategy = persisted_strategy(db); other = persisted_strategy(db, StrategyScope(2)); db.commit()
    assert client.post("/strategy-resources/not-a-uuid/simulations", headers=HEADERS, json=payload()).status_code == 422
    inaccessible = create(client, other, headers={**HEADERS, "Idempotency-Key": "other"})
    assert inaccessible.status_code == 404 and inaccessible.json()["detail"] == "Strategy not found"
    assert runner.calls == []
    assert create(client, strategy).status_code == 201
    conflict = create(client, strategy, body=payload(title="Different"))
    assert conflict.status_code == 409 and len(runner.calls) == 1


def test_generation_and_persistence_errors_are_safely_mapped(api, monkeypatch):
    client, db, _, _, _ = api
    strategy = persisted_strategy(db); db.commit()
    class Failure:
        def __init__(self, error): self.error = error
        def create_strategy_stress_test(self, *args, **kwargs): raise self.error
    for error, expected, secret in (
        (SimulationApplicationGenerationError("private provider"), 502, "private provider"),
        (SimulationApplicationPersistenceError("private database"), 503, "private database"),
    ):
        monkeypatch.setattr(resource_routes, "simulation_application_service", Failure(error))
        response = create(client, strategy, headers={**HEADERS, "Idempotency-Key": str(expected)})
        assert response.status_code == expected and secret not in response.text


def test_personal_list_and_detail_are_scoped_and_archived_list_is_hidden(api):
    client, db, _, _, _ = api
    own = persisted_strategy(db); other = persisted_strategy(db, StrategyScope(2)); db.commit()
    own_created = create(client, own, headers={**HEADERS, "Idempotency-Key": "own"}).json()
    # Create another user's Simulation directly through the same canonical application service.
    scenario = SimulationScenario("adverse", "Adverse", "Demand rises.", ("Demand changes.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.HIGH)
    from app.simulation.application import CreateStrategyStressTestCommand
    resource_routes.simulation_application_service.create_strategy_stress_test(
        db, command=CreateStrategyStressTestCommand(other.public_id, (scenario,), (UserSimulationAssumption("Staffing remains fixed.", "adverse"),), "Other", "other-key"),
        actor_user_id=2, scope=StrategyScope(2),
    )
    listed = client.get("/simulation-resources", headers={"Authorization": "Bearer token"})
    assert listed.status_code == 200
    assert [item["simulation_public_id"] for item in listed.json()["items"]] == [own_created["simulation_public_id"]]
    detail = client.get(f"/simulation-resources/{own_created['simulation_public_id']}", headers={"Authorization": "Bearer token"})
    assert detail.status_code == 200 and detail.json()["result"]["limitations"][0]["code"] == "not_calibrated"
    other_id = db.execute(select(simulation_resource_table.c.public_id).where(simulation_resource_table.c.owner_user_id == 2)).scalar_one()
    assert client.get(f"/simulation-resources/{other_id}", headers={"Authorization": "Bearer token"}).status_code == 404
    db.execute(update(simulation_resource_table).where(simulation_resource_table.c.public_id == own_created["simulation_public_id"]).values(archived_at=datetime(2026, 1, 1, tzinfo=timezone.utc))); db.commit()
    assert client.get("/simulation-resources", headers={"Authorization": "Bearer token"}).json()["items"] == []
    assert client.get(f"/simulation-resources/{own_created['simulation_public_id']}", headers={"Authorization": "Bearer token"}).status_code == 200


def test_workspace_list_and_detail_are_exact_scope_and_opaque(api):
    client, db, _, identity, _ = api
    identity["value"] = WORKSPACE
    one = persisted_strategy(db, StrategyScope(1, 10, 11)); two = persisted_strategy(db, StrategyScope(1, 10, 12)); db.commit()
    created = create(client, one, headers={**HEADERS, "Idempotency-Key": "workspace-one"}).json()
    identity["value"] = {**WORKSPACE, "workspace": {"id": 12}}
    hidden = create(client, two, headers={**HEADERS, "Idempotency-Key": "workspace-two"}).json()
    assert client.get(f"/simulation-resources/{created['simulation_public_id']}", headers={"Authorization": "Bearer token"}).status_code == 404
    listed = client.get("/simulation-resources", headers={"Authorization": "Bearer token"}).json()["items"]
    assert [item["simulation_public_id"] for item in listed] == [hidden["simulation_public_id"]]
    identity["value"] = {"user": {"id": 2}, "organization": {"id": 20, "account_type": "business"}, "workspace": {"id": 21}}
    assert client.get(f"/simulation-resources/{hidden['simulation_public_id']}", headers={"Authorization": "Bearer token"}).status_code == 404


def test_authentication_and_openapi_contract():
    app = FastAPI(); app.include_router(resource_routes.router)
    client = TestClient(app)
    assert client.get("/simulation-resources").status_code == 403
    assert client.get("/simulation-resources/00000000-0000-4000-8000-000000000001").status_code == 403
    assert client.post("/strategy-resources/00000000-0000-4000-8000-000000000001/simulations", headers={"Idempotency-Key": "key"}, json=payload()).status_code == 403
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/strategy-resources/{strategy_public_id}/simulations" in paths
    assert "/simulation-resources" in paths
    assert "/simulation-resources/{simulation_public_id}" in paths
    post = paths["/strategy-resources/{strategy_public_id}/simulations"]["post"]
    assert any(item["name"] == "Idempotency-Key" and item["required"] for item in post["parameters"])
    descriptions = json.dumps(post).casefold()
    assert "strategy stress test" in descriptions and "scenario analysis" in descriptions
    assert "calibrated forecast" not in descriptions
    assert {"201", "401", "403", "404", "409", "422", "500", "502", "503"} <= set(post["responses"])
    assert {"200", "401", "403", "422", "500", "503"} <= set(paths["/simulation-resources"]["get"]["responses"])
    assert {"200", "401", "403", "404", "422", "500", "503"} <= set(paths["/simulation-resources/{simulation_public_id}"]["get"]["responses"])
    assert "SimulationPublicErrorResponse" in schema["components"]["schemas"]
    assert not ({"/simulation/save", "/simulation/history", "/system/run_stream"} & set(paths))
