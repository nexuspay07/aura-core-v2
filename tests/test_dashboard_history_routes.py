from fastapi.testclient import TestClient

import app.main as main


class _Session:
    def close(self):
        pass


async def _identity(_credentials):
    return {"organization": {"id": 41}}


def test_dashboard_uses_authenticated_organization_history(monkeypatch):
    captured = {}
    monkeypatch.setattr(main, "get_current_user_from_token", _identity)
    monkeypatch.setattr(main, "SessionLocal", _Session)
    monkeypatch.setattr(
        main.history_engine,
        "get",
        lambda *, db, organization_id: captured.update(db=db, organization_id=organization_id) or [
            {"result": {"best_strategy": {"final_score": 9}}}
        ],
    )

    response = TestClient(main.app).get("/dashboard", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json()["total_runs"] == 1
    assert response.json()["average_score"] == 9
    assert captured["organization_id"] == 41


def test_history_route_uses_authenticated_organization(monkeypatch):
    captured = {}
    monkeypatch.setattr(main, "get_current_user_from_token", _identity)
    monkeypatch.setattr(main, "SessionLocal", _Session)
    monkeypatch.setattr(
        main.history_engine,
        "get",
        lambda *, db, organization_id: captured.update(organization_id=organization_id) or [],
    )

    response = TestClient(main.app).get("/lab/history", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == []
    assert captured["organization_id"] == 41
