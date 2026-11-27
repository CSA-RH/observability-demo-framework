"""Authorization: `obs-admin` manages users and acts on anyone; other users only on themselves."""
import pytest

from conftest import ADMIN_USER, TEST_USER, wait_for_operation

OTHER_USER = "someone"

SIMULATION = {
    "agents": [{"id": "waiter-duda", "type": "waiter"}],
    "layout": [],
    "user": {"username": TEST_USER, "monitoringType": "coo"},
}
CUSTOM_ALERT = {
    "name": "HighLatency",
    "scope": "custom",
    "severity": "critical",
    "observabilityStack": "coo",
    "definition": {"evaluation": "1m", "expression": "latency > 1", "summary": "Too slow"},
}
METRIC = {"id": "waiter-duda", "metric": {"name": "m", "value": 1}}


def user_paths(user):
    base = f"/api/v1/users/{user}/simulation"
    return [
        ("get", base, None),
        ("post", base, SIMULATION),
        ("delete", base, None),
        ("post", f"{base}/kick/waiter-duda", {"dns": "x", "count": 1}),
        ("post", f"{base}/metrics", METRIC),
        ("put", f"{base}/metrics", METRIC),
        ("get", f"{base}/alerts", None),
        ("post", f"{base}/alerts", CUSTOM_ALERT),
        ("delete", f"{base}/alerts/some-alert", None),
    ]


def call(client, method, path, body):
    return client.request(method, path, json=body) if body is not None else client.request(method, path)


# --- user management: admin only ------------------------------------------------------------------

@pytest.mark.parametrize("method, path, body", [
    ("get", "/api/v1/users", None),
    ("post", "/api/v1/users", {"username": "abc", "monitoringType": "coo"}),
    ("delete", f"/api/v1/users/{TEST_USER}", None),
])
def test_regular_user_cannot_manage_users(client, method, path, body):
    response = call(client, method, path, body)
    assert response.status_code == 403
    assert response.json() == {"message": "Forbidden: requires the 'obs-admin' role"}


def test_rejected_user_creation_has_no_side_effects(client, admin_client, login):
    login(TEST_USER)
    assert client.post("/api/v1/users", json={"username": "abc"}).status_code == 403
    login(ADMIN_USER, admin=True)
    assert admin_client.get("/api/v1/users").json() == []


def test_username_admin_without_the_role_is_a_regular_user(client, login):
    login("admin")
    assert client.get("/api/v1/users").status_code == 403


# --- /users/{user_id}/...: that user or an admin ---------------------------------------------------

@pytest.mark.parametrize("method, path, body", user_paths(OTHER_USER))
def test_regular_user_cannot_act_on_another_user(client, method, path, body):
    response = call(client, method, path, body)
    assert response.status_code == 403
    assert response.json() == {"message": f"Forbidden: {TEST_USER} cannot act on user {OTHER_USER}"}


@pytest.mark.parametrize("method, path, body", user_paths(TEST_USER))
def test_regular_user_can_act_on_themselves(client, method, path, body):
    assert call(client, method, path, body).status_code != 403


@pytest.mark.parametrize("method, path, body", user_paths(OTHER_USER))
def test_admin_can_act_on_any_user(admin_client, method, path, body):
    assert call(admin_client, method, path, body).status_code != 403


def test_rejected_simulation_is_not_created(client, admin_client, login):
    login(TEST_USER)  # fixtures share one identity: admin_client logged in last
    assert client.post(f"/api/v1/users/{OTHER_USER}/simulation", json=SIMULATION).status_code == 403
    login(ADMIN_USER, admin=True)
    assert admin_client.get(f"/api/v1/users/{OTHER_USER}/simulation").status_code == 404


# --- operations: owners and admins ----------------------------------------------------------------

def test_user_sees_own_operations_only(client, login):
    operation_id = client.post(f"/api/v1/users/{TEST_USER}/simulation", json=SIMULATION).json()["operationId"]
    assert wait_for_operation(client, operation_id)["status"] == "succeeded"

    login(OTHER_USER)
    response = client.get(f"/api/v1/operations/{operation_id}")
    assert response.status_code == 404
    assert response.json() == {"message": "Operation not found"}

    login(ADMIN_USER, admin=True)
    assert client.get(f"/api/v1/operations/{operation_id}").status_code == 200


def test_user_management_operations_are_admin_only(admin_client, login):
    operation_id = admin_client.post("/api/v1/users", json={"username": TEST_USER}).json()["operationId"]
    wait_for_operation(admin_client, operation_id)
    login(TEST_USER)  # even the user being created
    assert admin_client.get(f"/api/v1/operations/{operation_id}").status_code == 404
