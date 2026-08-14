"""Security contract tests for the canonical /marketplace route family."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.marketplace_routes as routes
from app.db.strategy import metadata, strategies


def _identity(user=1, organization=1, workspace=1):
    return {
        "user": {"id": user},
        "organization": {"id": organization},
        "workspace": {"id": workspace},
    }


def _client(monkeypatch, identity=None):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    async def current(_):
        if identity is None:
            raise HTTPException(401, "Invalid token")
        return identity

    monkeypatch.setattr(routes, "SessionLocal", factory)
    monkeypatch.setattr(routes, "get_current_user_from_token", current)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), factory, engine


def _seed(factory, *rows):
    db = factory()
    try:
        for row in rows:
            db.execute(insert(strategies).values(**row))
        db.commit()
    finally:
        db.close()


def test_marketplace_requires_valid_authentication(monkeypatch):
    client, _, engine = _client(monkeypatch)
    try:
        response = client.post(
            "/marketplace/save", headers={"Authorization": "Bearer invalid"}, json={"name": "x"}
        )
        assert response.status_code == 401
    finally:
        engine.dispose()


def test_creation_derives_all_ownership_from_authenticated_identity(monkeypatch):
    client, factory, engine = _client(monkeypatch, _identity())
    try:
        response = client.post(
            "/marketplace/save",
            headers={"Authorization": "Bearer token"},
            json={
                "name": "Safe",
                "is_public": False,
                "data": {"user_id": 99, "organization_id": 99, "workspace_id": 99},
            },
        )
        assert response.status_code == 201
        db = factory()
        try:
            row = db.execute(select(strategies)).mappings().one()
        finally:
            db.close()
        assert (row["owner_user_id"], row["organization_id"], row["workspace_id"]) == (1, 1, 1)
        assert row["owner"] != "guest"
    finally:
        engine.dispose()


def test_public_and_legacy_guest_records_are_readable_without_reassignment(monkeypatch):
    client, factory, engine = _client(monkeypatch, _identity())
    try:
        _seed(factory, {"id": 1, "name": "legacy", "owner": "guest", "is_public": 1})
        response = client.get("/marketplace/all", headers={"Authorization": "Bearer token"})
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [1]
        assert response.json()[0]["owner_user_id"] is None
        assert client.get("/marketplace/1", headers={"Authorization": "Bearer token"}).status_code == 200
    finally:
        engine.dispose()


def test_private_records_are_hidden_from_other_user_and_other_organization(monkeypatch):
    client, factory, engine = _client(monkeypatch, _identity(user=1, organization=1, workspace=1))
    try:
        _seed(factory, {
            "id": 2, "name": "private", "owner_user_id": 1, "organization_id": 2,
            "workspace_id": 2, "is_public": 0,
        })
        assert client.get("/marketplace/2", headers={"Authorization": "Bearer token"}).status_code == 404
        assert client.delete("/marketplace/2", headers={"Authorization": "Bearer token"}).status_code == 404
    finally:
        engine.dispose()


def test_owner_can_delete_own_item_but_other_owner_cannot(monkeypatch):
    client, factory, engine = _client(monkeypatch, _identity())
    try:
        _seed(factory, {"id": 3, "name": "owned", "owner_user_id": 1, "organization_id": 1,
                        "workspace_id": 1, "is_public": 0})
        assert client.delete("/marketplace/3", headers={"Authorization": "Bearer token"}).status_code == 200
        _seed(factory, {"id": 4, "name": "other", "owner_user_id": 2, "organization_id": 1,
                        "workspace_id": 1, "is_public": 0})
        assert client.delete("/marketplace/4", headers={"Authorization": "Bearer token"}).status_code == 404
    finally:
        engine.dispose()


def test_malformed_payload_is_rejected_without_persistence(monkeypatch):
    client, factory, engine = _client(monkeypatch, _identity())
    try:
        response = client.post(
            "/marketplace/save", headers={"Authorization": "Bearer token"},
            json={"name": "", "category": "unsupported"},
        )
        assert response.status_code == 422
        db = factory()
        try:
            assert db.execute(select(strategies.c.id)).all() == []
        finally:
            db.close()
    finally:
        engine.dispose()


def test_canonical_and_legacy_route_contract(monkeypatch):
    client, _, engine = _client(monkeypatch, _identity())
    try:
        paths = {route.path for route in client.app.routes}
        assert "/marketplace/save" in paths
        assert "/strategy/all" not in paths
    finally:
        engine.dispose()
