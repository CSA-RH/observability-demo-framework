"""Backend singletons shared by the routers.

`CLUSTER_CONNECTOR=mock` / `AGENT_MANAGER=mock` select the in-memory implementations (local
development and tests). Routers access them as `deps.cluster_connector` (module attribute, not
`from ... import`) so they always see the current instance.
"""
from agent_manager.MockAgentManager import MockAgentManager
from agent_manager.OpenShiftAgentManager import OpenShiftAgentManager
from cluster_connector.MockClusterConnector import MockClusterConnector
from cluster_connector.OpenShiftClusterConnector import OpenShiftClusterConnector
from settings import settings


cluster_connector = MockClusterConnector() if settings.uses_mock_cluster else OpenShiftClusterConnector()
agent_manager = MockAgentManager() if settings.uses_mock_agents else OpenShiftAgentManager()
