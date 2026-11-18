import logging
from typing import Any, Dict, List

from kubernetes.client.rest import ApiException  # type: ignore

from services.interfaces import MonitoringService
from services.openshift.kube import (
    AGENT_SELECTOR, ConfigMapJson, KubeApis, create_route, delete_route, ignore_not_found, namespace_label,
)
from settings import NamespaceLayout

log = logging.getLogger(__name__)

ALERTS_CONFIGMAP = "obs-demo-fwk-alerts"
COO_GROUP = "monitoring.rhobs"          # Cluster Observability Operator (per-user MonitoringStack)
UWM_GROUP = "monitoring.coreos.com"     # Platform Prometheus operator (user workload monitoring)
# Namespace label set by the sync playbook from the user's `monitoringType`.
STACK_LABEL = "observability-stack"


def api_group(stack: str | None) -> str:
    return COO_GROUP if stack == "coo" else UWM_GROUP


class OpenShiftMonitoringService(MonitoringService):

    def __init__(self, apis: KubeApis, layout: NamespaceLayout):
        self._custom = apis.custom
        self._core = apis.core
        self._layout = layout
        self._store = ConfigMapJson(apis.core)

    def _namespace_stack(self, namespace: str) -> str | None:
        return namespace_label(self._core, namespace, STACK_LABEL)

    # --- metrics -------------------------------------------------------------------------------

    def create_monitoring_stack(self, user: str, stack: str) -> None:
        if stack != "coo":
            return
        namespace = self._layout.user_namespace(user)
        name = f"monitoring-stack-{user}"
        body = {
            "apiVersion": f"{COO_GROUP}/v1alpha1",
            "kind": "MonitoringStack",
            "metadata": {
                "name": name,
                "labels": {"observability-demo-framework": "coo", "monitoring-stack": user},
            },
            "spec": {
                "logLevel": "debug",
                "alertmanagerConfig": {"replicas": 1},
                "prometheusConfig": {"replicas": 1},
                "retention": "1d",
                "resourceSelector": {"matchLabels": {"monitoring-stack": user}},
            },
        }
        try:
            self._custom.create_namespaced_custom_object(
                group=COO_GROUP, version="v1alpha1", namespace=namespace, plural="monitoringstacks", body=body)
            log.info(f"MonitoringStack {name} created successfully.")
        except ApiException as e:
            log.error(f"Exception when creating MonitoringStack {name}: {e}")
            raise
        create_route(self._custom, namespace, f"alertmanager-{user}", f"{name}-alertmanager")
        create_route(self._custom, namespace, f"prometheus-{user}", f"{name}-prometheus")

    def create_service_monitor(self, user: str, agent_id: str, stack: str) -> None:
        namespace = self._layout.user_namespace(user)
        group = api_group(stack)
        labels = {"app": agent_id, "observability-demo-framework": "agent"}
        if stack == "coo":
            labels["monitoring-stack"] = user  # picked up by the user's MonitoringStack
        body = {
            "apiVersion": f"{group}/v1",
            "kind": "ServiceMonitor",
            "metadata": {"name": agent_id, "labels": labels},
            "spec": {
                "selector": {"matchLabels": {"app": agent_id}},
                "endpoints": [{"port": "metrics", "interval": "30s"}],
            },
        }
        try:
            self._custom.create_namespaced_custom_object(
                group=group, version="v1", namespace=namespace, plural="servicemonitors", body=body)
            log.info(f"ServiceMonitor {agent_id} [{group}] created successfully.")
        except ApiException as e:
            log.error(f"Exception when creating ServiceMonitor {agent_id} [{group}]: {e}")
            raise

    def delete_monitoring(self, user: str) -> None:
        namespace = self._layout.user_namespace(user)
        stack = self._namespace_stack(namespace)
        log.info(f"Observability stack: {stack}")
        group = api_group(stack)
        if stack == "coo":
            name = f"monitoring-stack-{user}"
            ignore_not_found(
                lambda: self._custom.delete_namespaced_custom_object(
                    group=COO_GROUP, version="v1alpha1", namespace=namespace, plural="monitoringstacks", name=name),
                f"MonitoringStack '{name}'", namespace)
            delete_route(self._custom, namespace, f"prometheus-{user}")
            delete_route(self._custom, namespace, f"alertmanager-{user}")

        for plural in ("servicemonitors", "prometheusrules"):
            objects = self._custom.list_namespaced_custom_object(
                group=group, version="v1", namespace=namespace, plural=plural, label_selector=AGENT_SELECTOR)
            for obj in objects.get("items", []):
                name = obj["metadata"]["name"]
                log.info(f"Deleting {plural}: {name}")
                self._custom.delete_namespaced_custom_object(
                    group=group, version="v1", namespace=namespace, plural=plural, name=name)

        ignore_not_found(lambda: self._core.delete_namespaced_config_map(ALERTS_CONFIGMAP, namespace),
                         f"ConfigMap '{ALERTS_CONFIGMAP}'", namespace)

    # --- alerts --------------------------------------------------------------------------------

    def create_alert(self, user, stack, id, name, severity, group, expression, summary):
        namespace = self._layout.user_namespace(user)
        rule_group = api_group(stack)
        labels = {"observability-demo-framework": "agent"}
        if stack == "coo":
            labels["monitoring-stack"] = user
        body = {
            "apiVersion": f"{rule_group}/v1",
            "kind": "PrometheusRule",
            "metadata": {"name": id, "namespace": namespace, "labels": labels},
            "spec": {
                "groups": [{
                    "name": group,
                    "rules": [{
                        "alert": name,
                        "annotations": {"summary": summary},
                        "expr": expression,
                        "for": "1m",
                        "labels": {"severity": severity},
                    }],
                }],
            },
        }
        try:
            self._custom.create_namespaced_custom_object(
                group=rule_group, version="v1", namespace=namespace, plural="prometheusrules", body=body)
            log.info(f"PrometheusRule '{id}' created successfully.")
            return {"success": True}
        except ApiException as e:
            log.error(f"Exception when creating PrometheusRule: {e}")
            return None

    def delete_alert(self, user: str, alert_name: str) -> Dict[str, Any]:
        namespace = self._layout.user_namespace(user)
        # COO users' rules live in monitoring.rhobs (previously always deleted from monitoring.coreos.com).
        group = api_group(self._namespace_stack(namespace))
        try:
            self._custom.delete_namespaced_custom_object(
                group=group, version="v1", namespace=namespace, plural="prometheusrules", name=alert_name)
            return {"success": True}
        except ApiException as e:
            if e.status == 404:
                log.warning(f"PrometheusRule '{alert_name}' not found in namespace '{namespace}'.")
            else:
                log.error(f"Failed to delete PrometheusRule '{alert_name}': {e}")
            return {"success": False, "error": e}

    def save_alert_definition(self, user: str, alert: Dict[str, Any]) -> None:
        namespace = self._layout.user_namespace(user)
        alerts = self._store.load(ALERTS_CONFIGMAP, "alerts", namespace)
        alerts.append(alert)
        self._store.save(ALERTS_CONFIGMAP, "alerts", namespace, alerts)

    def delete_alert_definition(self, user: str, alert_id: str) -> Dict[str, Any]:
        namespace = self._layout.user_namespace(user)
        try:
            alerts = self._store.load(ALERTS_CONFIGMAP, "alerts", namespace)
            self._store.save(ALERTS_CONFIGMAP, "alerts", namespace,
                             [item for item in alerts if item.get("id") != alert_id])
            return {"success": True}
        except ApiException as e:
            return {"success": False, "error": e}

    def get_alert_definitions(self, user: str) -> List[Dict[str, Any]]:
        return self._store.load(ALERTS_CONFIGMAP, "alerts", self._layout.user_namespace(user))
