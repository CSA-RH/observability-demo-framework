import main
from agent_manager.OpenShiftAgentManager import AgentRequestError
from conftest import TEST_USER

URL = f"/api/v1/users/{TEST_USER}/simulation/metrics"
METRIC = {"id": "cook-1", "ip": "1.2.3.4", "metric": {"name": "orders", "value": 5}}


def test_create_and_update_metric(client):
    response = client.post(URL, json=METRIC)
    assert response.status_code == 200
    assert response.json() == {"message": "Metric created"}

    updated = {**METRIC, "metric": {"name": "orders", "value": 9}}
    response = client.put(URL, json=updated)
    assert response.status_code == 200
    assert response.json() == {"message": "Metric updated"}

    metrics = main.agent_manager.get_agent_metrics(TEST_USER, "cook-1.ns.svc")
    assert metrics == [{"name": "orders", "value": 9}]


def test_method_is_passed_to_agent_manager(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main.agent_manager, "set_agent_metrics", lambda method, user, payload: calls.append(method))
    client.post(URL, json=METRIC)
    client.put(URL, json=METRIC)
    assert calls == ["POST", "PUT"]


def test_async_agent_manager_message_is_returned(client, monkeypatch):
    async def set_metrics(method, user, payload):
        return "agent says ok"

    monkeypatch.setattr(main.agent_manager, "set_agent_metrics", set_metrics)
    assert client.post(URL, json=METRIC).json() == {"message": "agent says ok"}


def test_agent_errors_are_mapped_to_http_status(client, monkeypatch):
    def fail(method, user, payload):
        raise AgentRequestError(409, "Metric already exists")

    monkeypatch.setattr(main.agent_manager, "set_agent_metrics", fail)
    response = client.post(URL, json=METRIC)
    assert response.status_code == 409
    assert response.json() == {"message": "Metric already exists"}
