import main
from conftest import TEST_USER

URL = f"/api/v1/users/{TEST_USER}/simulation/alerts"

METRIC_ALERT = {
    "scope": "metricAgent",
    "severity": "warning",
    "observabilityStack": "coo",
    "definition": {"agent": "fabrice-olinga", "metric": "orders", "expression": "≥", "value": 10},
}
CUSTOM_ALERT = {
    "name": "HighLatency",
    "scope": "custom",
    "severity": "critical",
    "observabilityStack": "user-workload",
    "definition": {"evaluation": "1m", "expression": "latency > 1", "summary": "Too slow"},
}


def test_create_metric_alert_builds_cluster_resource(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main.cluster_connector, "create_alert_resource", lambda *args: calls.append(args) or "ok")

    response = client.post(URL, json=METRIC_ALERT)
    assert response.status_code == 200
    assert response.json() == {
        "id": "fabrice-olinga-orders-toohigh-metricagent",
        "name": "fabrice-olinga_orders_TooHigh",
    }
    assert calls == [(
        TEST_USER,
        "coo",
        "fabrice-olinga-orders-toohigh-metricagent",
        "fabrice-olinga_orders_TooHigh",
        "warning",
        "fabrice-olinga",
        'orders{job="fabrice-olinga"}>=10',
        "Alert fabrice-olinga_orders_TooHigh TooHigh on fabrice-olinga",
    )]


def test_create_custom_alert(client):
    response = client.post(URL, json=CUSTOM_ALERT)
    assert response.status_code == 200
    assert response.json() == {"id": "highlatency-custom", "name": "HighLatency"}


def test_list_alerts(client):
    client.post(URL, json=METRIC_ALERT)
    client.post(URL, json=CUSTOM_ALERT)
    response = client.get(URL)
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "fabrice-olinga-orders-toohigh-metricagent",
            "name": "fabrice-olinga_orders_TooHigh",
            "severity": "warning",
            "scope": "metricAgent",
            "evaluation": "1m",
            "promQL": 'orders{job="fabrice-olinga"}>=10',
            "summary": "Alert fabrice-olinga_orders_TooHigh TooHigh on fabrice-olinga",
        },
        {
            "id": "highlatency-custom",
            "name": "HighLatency",
            "severity": "critical",
            "scope": "custom",
            "evaluation": "1m",
            "promQL": "latency > 1",
            "summary": "Too slow",
        },
    ]


def test_cluster_failure_returns_400_and_does_not_persist(client, monkeypatch):
    monkeypatch.setattr(main.cluster_connector, "create_alert_resource", lambda *args: None)
    response = client.post(URL, json=CUSTOM_ALERT)
    assert response.status_code == 400
    assert client.get(URL).json() == []


def test_delete_alert(client):
    alert_id = client.post(URL, json=CUSTOM_ALERT).json()["id"]
    response = client.delete(f"{URL}/{alert_id}")
    assert response.status_code == 200
    assert client.get(URL).json() == []


def test_delete_alert_reports_cluster_errors(client, monkeypatch):
    alert_id = client.post(URL, json=CUSTOM_ALERT).json()["id"]
    monkeypatch.setattr(
        main.cluster_connector, "delete_alert", lambda user, name: {"success": False, "error": RuntimeError("x")}
    )
    response = client.delete(f"{URL}/{alert_id}")
    assert response.status_code == 400
    assert "Error deleting OpenShift alert resource" in response.json()["message"]
