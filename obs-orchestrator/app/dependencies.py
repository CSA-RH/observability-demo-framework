"""Backend singletons shared by the routers.

`CLUSTER_CONNECTOR=mock` / `AGENT_MANAGER=mock` select the in-memory implementations (local
development and tests). Routers access them as `deps.cluster_connector` (module attribute, not
`from ... import`) so they always see the current instance.
"""
import os

from agent_manager.MockAgentManager import MockAgentManager
from agent_manager.OpenShiftAgentManager import OpenShiftAgentManager
from cluster_connector.MockClusterConnector import MockClusterConnector
from cluster_connector.OpenShiftClusterConnector import OpenShiftClusterConnector


def is_using_fake_cluster_connector():
    return os.environ.get('CLUSTER_CONNECTOR') == 'mock'


def is_using_fake_agent_manager():
    return os.environ.get('AGENT_MANAGER') == 'mock'


cluster_connector = MockClusterConnector() if is_using_fake_cluster_connector() else OpenShiftClusterConnector()
agent_manager = MockAgentManager() if is_using_fake_agent_manager() else OpenShiftAgentManager()
