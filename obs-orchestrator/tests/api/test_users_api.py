import pytest

import main
from conftest import wait_for_operation


def create_user(client, username="abc", monitoring_type="coo"):
    response = client.post("/api/v1/users", json={"username": username, "monitoringType": monitoring_type})
    assert response.status_code == 202
    return response.json()


def test_list_users_initially_empty(client):
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert response.json() == []


def test_create_user_is_async_and_persists(client):
    body = create_user(client)
    assert body["status"] == "pending"

    operation = wait_for_operation(client, body["operationId"])
    assert operation["status"] == "succeeded"
    assert operation["type"] == "user-create"
    assert operation["metadata"]["username"] == "abc"
    assert client.get("/api/v1/users").json() == [{"username": "abc", "monitoringType": "coo"}]


@pytest.mark.parametrize("payload", [{}, {"username": "ab"}, {"username": "Bad_Name"}, {"username": "admin"}])
def test_create_user_rejects_invalid_username(client, payload):
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 400
    assert response.json()["message"]
    assert client.get("/api/v1/users").json() == []


def test_create_user_rolls_back_when_keycloak_sync_fails(client, monkeypatch):
    monkeypatch.setattr(main.cluster_connector, "sync_users", lambda: False)
    operation = wait_for_operation(client, create_user(client)["operationId"])
    assert operation["status"] == "failed"
    assert operation["error"] == "Keycloak user sync job failed"
    assert client.get("/api/v1/users").json() == []


@pytest.mark.xfail(strict=True, reason="Known gap: duplicate usernames are accepted (expected 409)")
def test_create_duplicate_user_is_rejected(client):
    wait_for_operation(client, create_user(client)["operationId"])
    response = client.post("/api/v1/users", json={"username": "abc"})
    assert response.status_code == 409


def test_delete_user(client):
    wait_for_operation(client, create_user(client, "abc")["operationId"])
    wait_for_operation(client, create_user(client, "def")["operationId"])

    response = client.delete("/api/v1/users/abc")
    assert response.status_code == 202
    operation = wait_for_operation(client, response.json()["operationId"])
    assert operation["status"] == "succeeded"
    assert [u["username"] for u in client.get("/api/v1/users").json()] == ["def"]


def test_delete_user_restores_list_when_sync_fails(client, monkeypatch):
    wait_for_operation(client, create_user(client)["operationId"])
    monkeypatch.setattr(main.cluster_connector, "sync_users", lambda: False)
    operation = wait_for_operation(client, client.delete("/api/v1/users/abc").json()["operationId"])
    assert operation["status"] == "failed"
    assert [u["username"] for u in client.get("/api/v1/users").json()] == ["abc"]


@pytest.mark.xfail(strict=True, reason="Known gap: deleting an unknown user succeeds (expected 404)")
def test_delete_unknown_user_returns_404(client):
    assert client.delete("/api/v1/users/ghost").status_code == 404


def test_unknown_operation_returns_404(client):
    response = client.get("/api/v1/operations/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"message": "Operation not found"}
