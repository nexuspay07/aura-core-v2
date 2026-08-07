from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.auth_routes as routes
from app.db.business_profile_table import business_profile_table
from app.db.database import metadata
from app.db.organization_member_table import organization_member_table
from app.db.organization_table import organization_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table


def _client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(routes, "SessionLocal", factory)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), factory, engine


def test_registration_defaults_to_business_and_returns_canonical_context(monkeypatch):
    client, factory, engine = _client(monkeypatch)
    try:
        response = client.post("/auth/register", json={"email": "business@example.com", "password": "password123", "full_name": "Taylor", "organization_name": "Taylor Co", "workspace_name": "Operations"})
        assert response.status_code == 200, response.text
        db = factory()
        organization = db.execute(select(organization_table)).mappings().one()
        workspace = db.execute(select(workspace_table)).mappings().one()
        assert organization["account_type"] == "business" and workspace["name"] == "Operations"
        assert db.execute(select(business_profile_table)).first() is not None
        db.close()
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
        assert me.status_code == 200
        assert me.json()["organization"]["account_type"] == "business"
        assert me.json()["organization"]["id"] == me.json()["workspace"]["organization_id"]
    finally:
        engine.dispose()


def test_personal_registration_is_profile_less_and_active_workspace_selection_is_persisted(monkeypatch):
    client, factory, engine = _client(monkeypatch)
    try:
        response = client.post("/auth/register", json={"email": "personal@example.com", "password": "password123", "account_type": "personal"})
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        db = factory()
        organization = db.execute(select(organization_table)).mappings().one()
        initial = db.execute(select(workspace_table)).mappings().one()
        db.execute(insert(workspace_table).values(organization_id=organization["id"], created_by_user_id=1, name="Second Space", slug="second-space", workspace_type="personal", is_active=True))
        second = db.execute(select(workspace_table).where(workspace_table.c.slug == "second-space")).mappings().one()
        db.execute(insert(workspace_member_table).values(workspace_id=second["id"], user_id=1, role="owner", status="active", is_active=True))
        db.commit()
        assert initial["workspace_type"] == "personal"
        assert db.execute(select(business_profile_table)).first() is None
        db.close()
        selected = client.post("/auth/context/workspace", headers={"Authorization": f"Bearer {token}"}, json={"workspace_id": second["id"]})
        assert selected.status_code == 200
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert me["workspace"]["id"] == second["id"] and me["organization"]["id"] == organization["id"]
    finally:
        engine.dispose()


def test_registration_rejects_invalid_account_type(monkeypatch):
    client, _, engine = _client(monkeypatch)
    try:
        assert client.post("/auth/register", json={"email": "invalid@example.com", "password": "password123", "account_type": "unsupported"}).status_code == 422
    finally:
        engine.dispose()
