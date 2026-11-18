"""Backend singletons shared by the routers.

`CLUSTER_CONNECTOR=mock` / `AGENT_MANAGER=mock` select the in-memory implementations (local
development and tests). Routers access them as `deps.tenants`, `deps.simulations`, ... (module
attributes, not `from ... import`) so they always see the current instance; `use()` swaps them.
"""
from agent_manager.MockAgentManager import MockAgentManager
from agent_manager.OpenShiftAgentManager import OpenShiftAgentManager
from services import Services, build_services
from settings import settings

tenants = simulations = monitoring = capabilities = operations = None


def use(services: Services) -> None:
    global tenants, simulations, monitoring, capabilities, operations
    tenants = services.tenants
    simulations = services.simulations
    monitoring = services.monitoring
    capabilities = services.capabilities
    operations = services.operations


use(build_services(settings))
agent_manager = MockAgentManager() if settings.uses_mock_agents else OpenShiftAgentManager()
