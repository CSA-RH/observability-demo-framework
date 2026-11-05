import pytest

import main
from conftest import TEST_USER, wait_for_operation

USER = TEST_USER

SIMULATION = {
    "agents": [
        {"id": "customer-fabrice-olinga", "type": "customer", "nextHop": ["waiter-duda"]},
        {"id": "waiter-duda", "type": "waiter"},
    ],
    "layout": [{"group": "nodes", "data": {"id": "customer-fabrice-olinga"}}],
    "user": {"username": USER, "monitoringType": "coo"},
}


def create_simulation(client, payload=SIMULATION):
    response = client.post(f"/api/v1/users/{USER}/simulation", json=payload)
    assert response.status_code == 202
    return wait_for_operation(client, response.json()["operationId"])


def test_get_simulation_returns_404_when_none(client):
    response = client.get(f"/api/v1/users/{USER}/simulation")
    assert response.status_code == 404
    assert response.json() == {"message": "Simulation not found"}


def test_create_simulation_runs_async_and_returns_deployed_agents(client):
    operation = create_simulation(client)
    assert operation["status"] == "succeeded"
    assert operation["type"] == "simulation-create"
    agents = operation["result"]
    assert [a["id"] for a in agents] == ["customer-fabrice-olinga", "waiter-duda"]
    assert all(a["ip"] and a["pod"].startswith(a["id"] + "-") for a in agents)


def test_get_simulation_after_create(client):
    create_simulation(client)
    response = client.get(f"/api/v1/users/{USER}/simulation")
    assert response.status_code == 200
    body = response.json()
    assert body["layout"] == SIMULATION["layout"]
    assert [a["id"] for a in body["agents"]] == ["customer-fabrice-olinga", "waiter-duda"]
    assert all(a["metrics"] == [] for a in body["agents"])


def test_create_simulation_with_malformed_payload_fails_operation(client):
    operation = create_simulation(client, {"agents": []})
    assert operation["status"] == "failed"
    assert operation["error"]


def test_create_simulation_failure_from_cluster_is_reported(client, monkeypatch):
    def boom(user, agents, stack):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(main.cluster_connector, "create_simulation_resources", boom)
    operation = create_simulation(client)
    assert operation["status"] == "failed"
    assert operation["error"] == "quota exceeded"
    assert client.get(f"/api/v1/users/{USER}/simulation").status_code == 404


def test_delete_simulation(client):
    create_simulation(client)
    response = client.delete(f"/api/v1/users/{USER}/simulation")
    assert response.status_code == 202
    operation = wait_for_operation(client, response.json()["operationId"])
    assert operation["status"] == "succeeded"
    assert client.get(f"/api/v1/users/{USER}/simulation").status_code == 404


def test_get_simulation_merges_metrics_and_their_alerts(client):
    create_simulation(client)
    agent = "customer-fabrice-olinga"
    client.post(
        f"/api/v1/users/{USER}/simulation/metrics",
        json={"id": agent, "ip": "1.2.3.4", "metric": {"name": "orders", "value": 5}},
    )
    client.post(
        f"/api/v1/users/{USER}/simulation/alerts",
        json={
            "scope": "metricAgent",
            "severity": "warning",
            "observabilityStack": "coo",
            "definition": {"agent": agent, "metric": "orders", "expression": ">", "value": 10},
        },
    )
    # Alerts for unknown agents/metrics are skipped, not errors.
    client.post(
        f"/api/v1/users/{USER}/simulation/alerts",
        json={
            "scope": "metricAgent",
            "severity": "warning",
            "observabilityStack": "coo",
            "definition": {"agent": "ghost", "metric": "orders", "expression": ">", "value": 1},
        },
    )

    body = client.get(f"/api/v1/users/{USER}/simulation").json()
    customer = next(a for a in body["agents"] if a["id"] == agent)
    assert [m["name"] for m in customer["metrics"]] == ["orders"]
    alerts = customer["metrics"][0]["alerts"]
    assert [a["name"] for a in alerts] == ["customer-fabrice-olinga_orders_StrictlyTooHigh"]


def test_kick_forwards_to_agent_manager(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main.agent_manager, "kick", lambda *args: calls.append(args) or {"ok": True})
    response = client.post(
        f"/api/v1/users/{USER}/simulation/kick/customer-1",
        json={"dns": "customer-1.ns.svc", "count": 4},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == [(USER, "customer-1", "customer-1.ns.svc", 4)]


@pytest.mark.xfail(strict=True, reason="Known gap: missing payload fields cause 500 (expected 422 validation)")
def test_kick_with_missing_fields_is_a_validation_error(client):
    response = client.post(f"/api/v1/users/{USER}/simulation/kick/customer-1", json={})
    assert response.status_code == 422
