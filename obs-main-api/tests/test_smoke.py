"""Smoke tests: the app boots with mock connectors and core endpoints answer.

Full endpoint characterization tests are tracked in ROADMAP.md (Phase 1).
"""
from conftest import TEST_USER


def test_cluster_info_uses_authenticated_user(client):
    response = client.get("/api/v1/escotilla")
    assert response.status_code == 200
    assert response.json()["Namespace"] == f"fake-namespace-{TEST_USER}"


def test_users_endpoint_returns_list(client):
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_endpoints_require_bearer_token():
    from fastapi.testclient import TestClient
    import main

    with TestClient(main.app) as c:
        assert c.get("/api/v1/users").status_code in (401, 403)
