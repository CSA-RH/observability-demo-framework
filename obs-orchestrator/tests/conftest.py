"""Shared fixtures.

Tests run the real FastAPI app against the mock connectors (no cluster, no Keycloak).
Mock storage is redirected to a per-test temporary directory so tests are isolated.
"""
import os
import time

import pytest

# Must be set before `main` is imported: it picks the implementations at import time.
os.environ.setdefault("CLUSTER_CONNECTOR", "mock")
os.environ.setdefault("AGENT_MANAGER", "mock")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from agent_manager.MockAgentManager import MockAgentManager  # noqa: E402
from cluster_connector.MockClusterConnector import MockClusterConnector  # noqa: E402
from utils import JSONUtils  # noqa: E402

TEST_USER = "tester"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Point every mock file path at tmp_path."""
    for attr, name in [
        ("PATH_SIMULATION_DEF", "sim.json"),
        ("PATH_ALERTS_DEF", "alerts.json"),
        ("PATH_USERS_DEF", "users.json"),
        ("PATH_OPERATIONS_DEF", "operations.json"),
    ]:
        monkeypatch.setattr(MockClusterConnector, attr, str(tmp_path / name))
    monkeypatch.setattr(MockAgentManager, "ROOT_METRICS_DIR", str(tmp_path))
    JSONUtils.save_json_to_file([], str(tmp_path / "users.json"))
    JSONUtils.save_json_to_file({}, str(tmp_path / "operations.json"))
    return tmp_path


@pytest.fixture
def client():
    """Authenticated client. Server errors are returned as HTTP 500 instead of raised."""
    main.app.dependency_overrides[main.get_current_user] = lambda: TEST_USER
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c
    main.app.dependency_overrides.clear()


@pytest.fixture
def anonymous_client():
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


def wait_for_operation(client, operation_id, timeout=5.0):
    """Poll an async operation until it leaves pending/running."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        operation = client.get(f"/api/v1/operations/{operation_id}").json()
        if operation["status"] not in ("pending", "running"):
            return operation
        time.sleep(0.02)
    raise AssertionError(f"Operation {operation_id} did not finish: {operation}")
