"""In-memory/file implementations of the domain services: local development without a cluster
(`CLUSTER_CONNECTOR=mock`) and the API tests. State lives in JSON files under `data_dir`."""
import logging
import os
import secrets
from typing import Any, Dict, List

from operations.operation_store import DocumentOperationStore
from services.interfaces import CapabilityService, MonitoringService, SimulationService, TenantService
from utils import JSONUtils

log = logging.getLogger(__name__)


class MockFiles:
    def __init__(self, data_dir: str = "/tmp"):
        self.simulation = os.path.join(data_dir, "obs-demo-fw-sim.json")
        self.alerts = os.path.join(data_dir, "obs-demo-fw-alerts.json")
        self.users = os.path.join(data_dir, "obs-demo-fw-users.json")
        self.operations = os.path.join(data_dir, "obs-demo-fw-operations.json")


def _pod_name(agent_id: str) -> str:
    return f"{agent_id}-{secrets.token_hex(5)[:9]}-{secrets.token_hex(3)[:5]}"


class MockTenantService(TenantService):
    def __init__(self, files: MockFiles):
        self._files = files
        if not os.path.exists(files.users):
            JSONUtils.save_json_to_file([], files.users)

    def get_users(self) -> List[Dict[str, Any]]:
        return JSONUtils.load_json_from_file(self._files.users) or []

    def save_users(self, users) -> None:
        JSONUtils.save_json_to_file(users, self._files.users)

    def sync_users(self) -> bool:
        return True


class MockMonitoringService(MonitoringService):
    def __init__(self, files: MockFiles):
        self._files = files

    def create_monitoring_stack(self, user, stack) -> None:
        pass

    def create_service_monitor(self, user, agent_id, stack) -> None:
        pass

    def delete_monitoring(self, user) -> None:
        JSONUtils.delete_json_file(self._files.alerts)

    def create_alert(self, user, stack, id, name, severity, group, expression, summary):
        log.info(f"Mocked alert {id} ({name}) for {user} [{stack}]: {severity}, {group}, {expression}, {summary}")
        return id

    def delete_alert(self, user, alert_name):
        return {"success": True}

    def save_alert_definition(self, user, alert) -> None:
        alerts = JSONUtils.load_json_from_file(self._files.alerts)
        alerts.append(alert)
        JSONUtils.save_json_to_file(alerts, self._files.alerts)

    def delete_alert_definition(self, user, alert_id):
        alerts = JSONUtils.load_json_from_file(self._files.alerts)
        JSONUtils.save_json_to_file([a for a in alerts if a.get("id") != alert_id], self._files.alerts)
        return {"success": True}

    def get_alert_definitions(self, user):
        return JSONUtils.load_json_from_file(self._files.alerts)


class MockSimulationService(SimulationService):
    def __init__(self, files: MockFiles, monitoring: MonitoringService):
        self._files = files
        self._monitoring = monitoring

    def create_resources(self, user, agents, stack):
        for agent in agents:
            agent["ip"] = "1.2.3.4"
            agent["pod"] = _pod_name(agent["id"])
        return agents

    def save(self, user, simulation) -> None:
        JSONUtils.save_json_to_file(simulation, self._files.simulation)

    def get(self, user):
        simulation = JSONUtils.load_json_from_file(self._files.simulation)
        if not simulation:
            return {}
        for agent in simulation["agents"]:
            agent["pod"] = _pod_name(agent["id"])
        return simulation

    def delete(self, user) -> None:
        self._monitoring.delete_monitoring(user)
        JSONUtils.delete_json_file(self._files.simulation)

    def agent_hostname(self, user, agent_id):
        return f"{agent_id}.fake-namespace-{user}.svc"


class MockCapabilityService(CapabilityService):
    def get_cluster_info(self, user):
        return {
            "Connected": True,
            "Name": "Fake Cluster",
            "Namespace": f"fake-namespace-{user}",
            "AppNamespace": "fake-namespace",
            "UserNamespacePrefix": "fake-namespace-",
            "ConsoleURL": "https://redhat.com",
            "apiLogsURL": "https://redhat.com",
            "JaegerUI": "https://redhat.com",
            "GrafanaURL": "https://ibm.com",
        }


class FileOperationStore(DocumentOperationStore):
    def __init__(self, files: MockFiles):
        self._path = files.operations
        if not os.path.exists(self._path):
            JSONUtils.save_json_to_file({}, self._path)

    def _load(self):
        return JSONUtils.load_json_from_file(self._path)

    def _save(self, operations) -> None:
        JSONUtils.save_json_to_file(operations, self._path)
