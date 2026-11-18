"""Async operation workflows, tested against one in-memory fake playing every service."""
import asyncio

import pytest

from operations.operation_store import new_operation
from operations.operation_tasks import (
    run_simulation_create,
    run_simulation_delete,
    run_user_create,
    run_user_delete,
)


class FakeServices:
    """OperationStore + TenantService + SimulationService."""

    def __init__(self, users=None, sync_result=True, sync_error=None):
        self.users = list(users or [])
        self.sync_result = sync_result
        self.sync_error = sync_error
        self.operations = {}
        self.saved_simulation = None
        self.deleted_simulation_for = None
        self.fail_create = False

    # operations
    def create(self, operation_type, metadata=None):
        operation = new_operation(operation_type, metadata)
        self.operations[operation["id"]] = operation
        return operation["id"]

    def get(self, operation_id):
        return self.operations.get(operation_id)

    get_operation = get

    def update(self, operation_id, status=None, error=None, result=None, metadata=None):
        operation = self.operations[operation_id]
        for key, value in (("status", status), ("error", error), ("result", result), ("metadata", metadata)):
            if value is not None:
                operation[key] = value

    # users
    def get_users(self):
        return list(self.users)

    def save_users(self, users):
        self.users = list(users)

    def sync_users(self):
        if self.sync_error:
            raise self.sync_error
        return self.sync_result

    # simulation
    def create_resources(self, user, agents, stack):
        if self.fail_create:
            raise RuntimeError("quota exceeded")
        return [dict(agent, ip="10.0.0.1", stack=stack) for agent in agents]

    def save(self, user, payload):
        self.saved_simulation = (user, payload)

    def delete(self, user):
        self.deleted_simulation_for = user


def run(coro):
    return asyncio.run(coro)


def test_user_create_succeeds_and_persists_user():
    connector = FakeServices()
    op = connector.create("user-create")
    run(run_user_create(connector, connector, op, {"username": "abc"}))
    assert connector.get_operation(op)["status"] == "succeeded"
    assert connector.get_operation(op)["metadata"]["message"]
    assert connector.users == [{"username": "abc"}]


@pytest.mark.parametrize(
    "connector_kwargs, error",
    [
        ({"sync_result": False}, "Keycloak user sync job failed"),
        ({"sync_error": RuntimeError("boom")}, "boom"),
    ],
)
def test_user_create_rolls_back_on_sync_failure(connector_kwargs, error):
    connector = FakeServices(users=[{"username": "existing"}], **connector_kwargs)
    op = connector.create("user-create")
    run(run_user_create(connector, connector, op, {"username": "abc"}))
    assert connector.get_operation(op)["status"] == "failed"
    assert connector.get_operation(op)["error"] == error
    assert connector.users == [{"username": "existing"}]


def test_user_delete_succeeds():
    connector = FakeServices(users=[{"username": "abc"}, {"username": "def"}])
    op = connector.create("user-delete")
    run(run_user_delete(connector, connector, op, "abc"))
    assert connector.get_operation(op)["status"] == "succeeded"
    assert connector.users == [{"username": "def"}]


@pytest.mark.parametrize("connector_kwargs", [{"sync_result": False}, {"sync_error": RuntimeError("boom")}])
def test_user_delete_restores_previous_users_on_failure(connector_kwargs):
    previous = [{"username": "abc"}, {"username": "def"}]
    connector = FakeServices(users=previous, **connector_kwargs)
    op = connector.create("user-delete")
    run(run_user_delete(connector, connector, op, "abc"))
    assert connector.get_operation(op)["status"] == "failed"
    assert connector.users == previous


def test_simulation_create_stores_result_and_saves_payload():
    connector = FakeServices()
    op = connector.create("simulation-create")
    payload = {"agents": [{"id": "a"}], "user": {"monitoringType": "coo"}}
    run(run_simulation_create(connector, connector, op, "abc", payload))
    operation = connector.get_operation(op)
    assert operation["status"] == "succeeded"
    assert operation["result"] == [{"id": "a", "ip": "10.0.0.1", "stack": "coo"}]
    assert connector.saved_simulation == ("abc", payload)


def test_simulation_create_failure_is_recorded_and_nothing_saved():
    connector = FakeServices()
    connector.fail_create = True
    op = connector.create("simulation-create")
    run(run_simulation_create(connector, connector, op, "abc", {"agents": [], "user": {"monitoringType": "coo"}}))
    assert connector.get_operation(op)["status"] == "failed"
    assert connector.get_operation(op)["error"] == "quota exceeded"
    assert connector.saved_simulation is None


@pytest.mark.parametrize("async_agent_manager", [False, True])
def test_simulation_delete_cleans_cluster_and_agent_metrics(async_agent_manager):
    calls = []

    class AgentManager:
        if async_agent_manager:
            async def delete_metrics_definitions(self, user_id):
                calls.append(user_id)
        else:
            def delete_metrics_definitions(self, user_id):
                calls.append(user_id)

    connector = FakeServices()
    op = connector.create("simulation-delete")
    run(run_simulation_delete(connector, connector, op, "abc", AgentManager()))
    assert connector.get_operation(op)["status"] == "succeeded"
    assert connector.deleted_simulation_for == "abc"
    assert calls == ["abc"]
