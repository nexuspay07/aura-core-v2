"""Security tests for the canonical authenticated /lab/simulate contract."""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main
from app.db.database import metadata
from app.db.simulation_history_table import simulation_history_table


def _identity(user=7, organization=8, workspace=9):
    return {
        "user": {"id": user},
        "organization": {"id": organization},
        "workspace": {"id": workspace},
    }


def _configure_authenticated_client(monkeypatch, identity):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    async def current(_):
        if identity is None:
            raise HTTPException(401, "Invalid token")
        return identity

    monkeypatch.setattr(main, "SessionLocal", factory)
    monkeypatch.setattr(main, "get_current_user_from_token", current)
    return TestClient(main.app, raise_server_exceptions=False), factory, engine


def test_simulation_requires_authentication_and_legacy_routes_are_unmounted():
    client = TestClient(main.app, raise_server_exceptions=False)
    assert client.post("/lab/simulate", json={"goal": "test"}).status_code == 403
    paths = {route.path for route in main.app.routes}
    assert "/lab/simulate" in paths
    assert "/strategy/all" not in paths


def test_simulation_rejects_incomplete_authenticated_context(monkeypatch):
    client, _, engine = _configure_authenticated_client(monkeypatch, {"user": {"id": 7}})
    try:
        assert client.post(
            "/lab/simulate", headers={"Authorization": "Bearer token"}, json={"goal": "test"}
        ).status_code == 409
    finally:
        engine.dispose()


def test_simulation_engine_failure_is_safe_and_does_not_persist_history(monkeypatch):
    client, factory, engine = _configure_authenticated_client(monkeypatch, _identity())
    monkeypatch.setattr(
        main.simulation_engine,
        "run_simulation",
        lambda *_: (_ for _ in ()).throw(RuntimeError("private traceback")),
    )
    try:
        response = client.post(
            "/lab/simulate", headers={"Authorization": "Bearer token"},
            json={"goal": "test", "organization_id": 99, "workspace_id": 99},
        )
        assert response.status_code == 422
        assert "private traceback" not in response.text
        db = factory()
        try:
            assert db.execute(select(simulation_history_table.c.id)).all() == []
        finally:
            db.close()
    finally:
        engine.dispose()


def test_successful_simulation_persists_canonical_identity_not_client_values(monkeypatch):
    client, factory, engine = _configure_authenticated_client(monkeypatch, _identity())
    captured = {}

    def save(*, db, organization_id, workspace_id, user_id, goal, scenario, result):
        captured.update(
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            goal=goal,
            scenario=scenario,
        )
        return 1

    monkeypatch.setattr(main.history_engine, "save", save)
    monkeypatch.setattr(main.simulation_engine, "run_simulation", lambda *_: {"results": [{"name": "safe"}]})
    monkeypatch.setattr(main.world_engine, "build_world", lambda *_: {})
    monkeypatch.setattr(main.world_engine, "apply_world", lambda results, _: results)
    monkeypatch.setattr(main.causal_reasoning_engine, "analyze_causality", lambda world, **_: world)
    monkeypatch.setattr(main, "add_prediction_and_uncertainty", lambda results, _: results)

    async def learn(*_):
        return {}

    monkeypatch.setattr(main.learning_engine, "learn", learn)
    monkeypatch.setattr(main.learning_engine, "apply_learning", lambda results, *_: results)
    monkeypatch.setattr(main.debate_engine, "run_debate", lambda results, _: (results, []))
    monkeypatch.setattr(main.agent_engine, "run_agents", lambda _: [])
    monkeypatch.setattr(main.failure_engine, "predict", lambda *_: [])
    monkeypatch.setattr(main, "add_strategy_enrichment", lambda results, _: results)
    monkeypatch.setattr(main.explanation_engine, "generate", lambda *_args, **_kwargs: "safe")
    monkeypatch.setattr(main, "generate_action_plan", lambda _: {})

    try:
        response = client.post(
            "/lab/simulate", headers={"Authorization": "Bearer token"},
            json={"goal": "Canonical identity", "organization_id": 99, "workspace_id": 99},
        )
        assert response.status_code == 200
        assert captured["user_id"] == 7
        assert captured["organization_id"] == 8
        assert captured["workspace_id"] == 9
        assert "test_user" not in str(captured)
    finally:
        engine.dispose()


def test_history_is_scoped_to_the_authenticated_organization(monkeypatch):
    client, factory, engine = _configure_authenticated_client(monkeypatch, _identity(7, 8, 9))
    try:
        db = factory()
        try:
            db.execute(simulation_history_table.insert().values(
                organization_id=8, workspace_id=9, user_id=7, goal="owned", scenario={}, result={}
            ))
            db.execute(simulation_history_table.insert().values(
                organization_id=10, workspace_id=11, user_id=12, goal="other", scenario={}, result={}
            ))
            db.commit()
        finally:
            db.close()
        response = client.get("/lab/history", headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        assert [item["goal"] for item in response.json()] == ["owned"]
    finally:
        engine.dispose()
