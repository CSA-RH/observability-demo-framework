"""Domain service interfaces.

Each service owns one concern of the orchestrator. There are two implementations of each:
`services.openshift` (Kubernetes API) and `services.mock` (local files, for development and tests).
Wiring happens in `services.build_services`.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class TenantService(ABC):
    """Lab users: the user registry and its synchronisation to Keycloak and user namespaces."""

    @abstractmethod
    def get_users(self) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def save_users(self, users: List[Dict[str, Any]]) -> None:
        ...

    @abstractmethod
    def sync_users(self) -> bool:
        """Apply the registry (Keycloak users, namespaces, bindings). False if the sync failed."""


class MonitoringService(ABC):
    """Metrics collection (COO MonitoringStack or user workload monitoring) and alerts."""

    @abstractmethod
    def create_monitoring_stack(self, user: str, stack: str) -> None:
        """Per-user monitoring resources needed before agents can be scraped (COO only)."""

    @abstractmethod
    def create_service_monitor(self, user: str, agent_id: str, stack: str) -> None:
        ...

    @abstractmethod
    def delete_monitoring(self, user: str) -> None:
        """Remove every monitoring resource and alert of the user's simulation."""

    @abstractmethod
    def create_alert(self, user: str, stack: str, id: str, name: str, severity: str, group: str,
                     expression: str, summary: str) -> Any:
        """Create the PrometheusRule. Returns None on failure."""

    @abstractmethod
    def delete_alert(self, user: str, alert_name: str) -> Dict[str, Any]:
        """Delete the PrometheusRule. Returns {"success": bool, "error": exc?}."""

    @abstractmethod
    def save_alert_definition(self, user: str, alert: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete_alert_definition(self, user: str, alert_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_alert_definitions(self, user: str) -> List[Dict[str, Any]]:
        ...


class SimulationService(ABC):
    """Agent workloads (Deployments, Services) and the stored simulation definition."""

    @abstractmethod
    def create_resources(self, user: str, agents: List[Dict[str, Any]], stack: str) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def save(self, user: str, simulation: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get(self, user: str) -> Dict[str, Any]:
        """The stored simulation with current pod names, or {} if there is none."""

    @abstractmethod
    def delete(self, user: str) -> None:
        ...

    @abstractmethod
    def agent_hostname(self, user: str, agent_id: str) -> str:
        ...


class CapabilityService(ABC):
    """What the cluster offers: identity, console links, namespace layout (Phase 4: operators)."""

    @abstractmethod
    def get_cluster_info(self, user: str) -> Dict[str, Any]:
        ...


class OperationStore(ABC):
    """Persistence of async operations (status polled by the console)."""

    @abstractmethod
    def create(self, operation_type: str, metadata: Dict[str, Any] | None = None) -> str:
        ...

    @abstractmethod
    def get(self, operation_id: str) -> Dict[str, Any] | None:
        ...

    @abstractmethod
    def update(self, operation_id: str, status: str | None = None, error: str | None = None,
               result: Any = None, metadata: Dict[str, Any] | None = None) -> None:
        ...
