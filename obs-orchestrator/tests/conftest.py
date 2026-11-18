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

import auth  # noqa: E402
import dependencies as deps  # noqa: E402
import main  # noqa: E402
from agent_manager.MockAgentManager import MockAgentManager  # noqa: E402
from services import build_mock_services  # noqa: E402

TEST_USER = "tester"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Fresh mock services storing their state in tmp_path."""
    services = build_mock_services(str(tmp_path))
    for name in ("tenants", "simulations", "monitoring", "capabilities", "operations"):
        monkeypatch.setattr(deps, name, getattr(services, name))
    monkeypatch.setattr(MockAgentManager, "ROOT_METRICS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client():
    """Authenticated client. Server errors are returned as HTTP 500 instead of raised."""
    main.app.dependency_overrides[auth.get_current_user] = lambda: TEST_USER
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
