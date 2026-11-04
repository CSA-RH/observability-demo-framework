import os
import sys
from pathlib import Path

import pytest

# The app uses flat imports (e.g. `from utils import ...`), so put app/ on the path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

# Run against the mock implementations: no cluster or Keycloak required.
os.environ.setdefault("CLUSTER_CONNECTOR", "mock")
os.environ.setdefault("AGENT_MANAGER", "mock")

TEST_USER = "tester"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    import main

    main.app.dependency_overrides[main.get_current_user] = lambda: TEST_USER
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
