import pytest

import dependencies as deps
from conftest import wait_for_operation


def create_user(client, username="abc", monitoring_type="coo"):
    response = client.post("/api/v1/users", json={"username": username, "monitoringType": monitoring_type})
    assert response.status_code == 202
    return response.json()


def test_list_users_initially_empty(admin_client):
    response = admin_client.get("/api/v1/users")
    assert response.status_code == 200
    assert response.json() == []


def test_create_user_is_async_and_persists(admin_client):
    body = create_user(admin_client)
    assert body["status"] == "pending"

    operation = wait_for_operation(admin_client, body["operationId"])
    assert operation["status"] == "succeeded"
    assert operation["type"] == "user-create"
    assert operation["metadata"]["username"] == "abc"
    assert admin_client.get("/api/v1/users").json() == [{"username": "abc", "monitoringType": "coo"}]


@pytest.mark.parametrize("payload", [{"username": "ab"}, {"username": "Bad_Name"}, {"username": "admin"}])
def test_create_user_rejects_invalid_username(admin_client, payload):
    response = admin_client.post("/api/v1/users", json=payload)
    assert response.status_code == 400
    assert response.json()["message"]
    assert admin_client.get("/api/v1/users").json() == []


def test_create_user_rolls_back_when_keycloak_sync_fails(admin_client, monkeypatch):
    monkeypatch.setattr(deps.tenants, "sync_users", lambda: False)
    operation = wait_for_operation(admin_client, create_user(admin_client)["operationId"])
    assert operation["status"] == "failed"
    assert operation["error"] == "Keycloak user sync job failed"
    assert admin_client.get("/api/v1/users").json() == []


def test_create_duplicate_user_is_rejected(admin_client):
    wait_for_operation(admin_client, create_user(admin_client)["operationId"])
    response = admin_client.post("/api/v1/users", json={"username": "abc"})
    assert response.status_code == 409
    assert response.json() == {"message": "User abc already exists"}
    assert len(admin_client.get("/api/v1/users").json()) == 1


@pytest.mark.parametrize("payload", [{}, {"username": 42}, {"monitoringType": "coo"}])
def test_create_user_with_missing_or_mistyped_username_is_422(admin_client, payload):
    response = admin_client.post("/api/v1/users", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["message"].startswith("Invalid request: username:")
    assert body["details"][0]["loc"] == ["body", "username"]


def test_delete_user(admin_client):
    wait_for_operation(admin_client, create_user(admin_client, "abc")["operationId"])
    wait_for_operation(admin_client, create_user(admin_client, "def")["operationId"])

    response = admin_client.delete("/api/v1/users/abc")
    assert response.status_code == 202
    operation = wait_for_operation(admin_client, response.json()["operationId"])
    assert operation["status"] == "succeeded"
    assert [u["username"] for u in admin_client.get("/api/v1/users").json()] == ["def"]


def test_delete_user_restores_list_when_sync_fails(admin_client, monkeypatch):
    wait_for_operation(admin_client, create_user(admin_client)["operationId"])
    monkeypatch.setattr(deps.tenants, "sync_users", lambda: False)
    operation = wait_for_operation(admin_client, admin_client.delete("/api/v1/users/abc").json()["operationId"])
    assert operation["status"] == "failed"
    assert [u["username"] for u in admin_client.get("/api/v1/users").json()] == ["abc"]


def test_delete_unknown_user_returns_404(admin_client):
    response = admin_client.delete("/api/v1/users/ghost")
    assert response.status_code == 404
    assert response.json() == {"message": "User ghost not found"}


def test_unknown_operation_returns_404(admin_client):
    response = admin_client.get("/api/v1/operations/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"message": "Operation not found"}
