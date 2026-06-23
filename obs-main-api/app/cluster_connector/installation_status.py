from __future__ import annotations

import re
from typing import Any, Callable
from kubernetes import client  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore


OPERATOR_CHECKS = (
    {"id": "rhbk-operator", "label": "RHBK Operator", "namespace": "openshift-operators"},
    {
        "id": "cluster-observability-operator",
        "label": "Cluster Observability Operator",
        "namespace": "openshift-operators",
    },
    {"id": "grafana-operator", "label": "Grafana Operator", "namespace": "openshift-operators"},
    {
        "id": "opentelemetry-product",
        "label": "OpenTelemetry Operator",
        "namespace": "openshift-opentelemetry-operator",
    },
)


def _component(component_id: str, label: str, installed: bool, detail: str) -> dict[str, Any]:
    return {
        "id": component_id,
        "label": label,
        "installed": installed,
        "detail": detail,
    }


def _operator(operator_id: str, label: str, installed: bool, detail: str) -> dict[str, Any]:
    return {
        "id": operator_id,
        "label": label,
        "installed": installed,
        "detail": detail,
    }


class InstallationStatusDetector:
    def __init__(
        self,
        core_api: client.CoreV1Api,
        custom_api: client.CustomObjectsApi,
        framework_namespace: str,
        route_lookup: Callable[[str, str], str | None],
    ):
        self._core_api = core_api
        self._custom_api = custom_api
        self._framework_namespace = framework_namespace
        self._route_lookup = route_lookup

    def detect(self) -> dict[str, Any]:
        return {
            "components": [
                self._detect_user_workload_monitoring(),
                self._detect_loki(),
                self._detect_tempo(),
                self._detect_opentelemetry(),
                self._detect_grafana(),
                self._detect_keycloak(),
                self._detect_coo(),
            ],
            "operators": [self._detect_operator(item) for item in OPERATOR_CHECKS],
        }

    def _detect_user_workload_monitoring(self) -> dict[str, Any]:
        try:
            config_map = self._core_api.read_namespaced_config_map(
                "cluster-monitoring-config",
                "openshift-monitoring",
            )
            raw_config = (config_map.data or {}).get("config.yaml", "")
            enabled = bool(re.search(r"enableUserWorkload:\s*true\b", raw_config))
            detail = (
                "enableUserWorkload: true"
                if enabled
                else "enableUserWorkload is not enabled in cluster-monitoring-config"
            )
            return _component("uwm", "User Workload Monitoring", enabled, detail)
        except ApiException as exc:
            if exc.status == 404:
                return _component(
                    "uwm",
                    "User Workload Monitoring",
                    False,
                    "cluster-monitoring-config not found in openshift-monitoring",
                )
            return _component("uwm", "User Workload Monitoring", False, f"Check failed: {exc.status}")
        except Exception as exc:
            return _component("uwm", "User Workload Monitoring", False, str(exc))

    def _detect_loki(self) -> dict[str, Any]:
        for namespace in ("openshift-logging", self._framework_namespace):
            items = self._list_custom_resources(
                group="loki.grafana.com",
                version="v1",
                namespace=namespace,
                plural="lokistacks",
            )
            if items:
                names = ", ".join(
                    item.get("metadata", {}).get("name", "unknown") for item in items
                )
                return _component(
                    "loki",
                    "Loki",
                    True,
                    f"LokiStack in {namespace}: {names}",
                )

        route = self._route_lookup("openshift-logging", "app.kubernetes.io/name=lokistack")
        if route:
            return _component("loki", "Loki", True, f"Route detected: {route}")

        return _component("loki", "Loki", False, "No LokiStack found")

    def _detect_tempo(self) -> dict[str, Any]:
        items = self._list_custom_resources(
            group="tempo.grafana.com",
            version="v1alpha1",
            namespace=self._framework_namespace,
            plural="tempostacks",
        )
        if items:
            names = ", ".join(item.get("metadata", {}).get("name", "unknown") for item in items)
            return _component("tempo", "Tempo", True, f"TempoStack: {names}")

        route = self._route_lookup(
            self._framework_namespace,
            "app.kubernetes.io/component=query-frontend",
        )
        if route:
            return _component("tempo", "Tempo", True, f"Query frontend route: {route}")

        return _component("tempo", "Tempo", False, "No TempoStack found in framework namespace")

    def _detect_opentelemetry(self) -> dict[str, Any]:
        instrumentations = self._list_custom_resources(
            group="opentelemetry.io",
            version="v1alpha1",
            namespace=self._framework_namespace,
            plural="instrumentations",
        )
        collectors = self._list_custom_resources(
            group="opentelemetry.io",
            version="v1beta1",
            namespace=self._framework_namespace,
            plural="opentelemetrycollectors",
        )
        if instrumentations or collectors:
            return _component(
                "opentelemetry",
                "OpenTelemetry",
                True,
                (
                    f"{len(instrumentations)} Instrumentation, "
                    f"{len(collectors)} OpenTelemetryCollector in {self._framework_namespace}"
                ),
            )

        operator = self._detect_operator(
            {
                "id": "opentelemetry-product",
                "label": "OpenTelemetry Operator",
                "namespace": "openshift-opentelemetry-operator",
            }
        )
        if operator["installed"]:
            return _component(
                "opentelemetry",
                "OpenTelemetry",
                True,
                f"Operator installed ({operator['detail']}); no framework Instrumentation yet",
            )

        return _component(
            "opentelemetry",
            "OpenTelemetry",
            False,
            "No Instrumentation or OpenTelemetryCollector in framework namespace",
        )

    def _detect_grafana(self) -> dict[str, Any]:
        route = self._route_lookup(self._framework_namespace, "observability-demo-framework=grafana")
        if route:
            return _component("grafana", "Grafana", True, route)
        return _component("grafana", "Grafana", False, "Grafana route not found")

    def _detect_keycloak(self) -> dict[str, Any]:
        route = self._route_lookup(self._framework_namespace, "app=keycloak")
        if route:
            return _component("keycloak", "Keycloak", True, route)

        try:
            self._custom_api.get_namespaced_custom_object(
                group="k8s.keycloak.org",
                version="v2alpha1",
                namespace=self._framework_namespace,
                plural="keycloaks",
                name="keycloak",
            )
            return _component("keycloak", "Keycloak", True, "Keycloak CR present")
        except ApiException as exc:
            if exc.status == 404:
                return _component("keycloak", "Keycloak", False, "Keycloak route/CR not found")
            return _component("keycloak", "Keycloak", False, f"Check failed: {exc.status}")
        except Exception as exc:
            return _component("keycloak", "Keycloak", False, str(exc))

    def _detect_coo(self) -> dict[str, Any]:
        items = self._list_custom_resources(
            group="monitoring.rhobs",
            version="v1",
            namespace=self._framework_namespace,
            plural="monitoringstacks",
        )
        if items:
            names = ", ".join(item.get("metadata", {}).get("name", "unknown") for item in items)
            return _component("coo", "Cluster Observability", True, f"MonitoringStack: {names}")
        return _component(
            "coo",
            "Cluster Observability",
            False,
            "No MonitoringStack in framework namespace",
        )

    def _detect_operator(self, operator: dict[str, str]) -> dict[str, Any]:
        try:
            subscription = self._custom_api.get_namespaced_custom_object(
                group="operators.coreos.com",
                version="v1alpha1",
                namespace=operator["namespace"],
                plural="subscriptions",
                name=operator["id"],
            )
            current_csv = subscription.get("status", {}).get("currentCSV")
            installed = bool(current_csv)
            detail = current_csv or "Subscription present without currentCSV"
            return _operator(operator["id"], operator["label"], installed, detail)
        except ApiException as exc:
            if exc.status == 404:
                return _operator(operator["id"], operator["label"], False, "Not subscribed")
            return _operator(operator["id"], operator["label"], False, f"Check failed: {exc.status}")
        except Exception as exc:
            return _operator(operator["id"], operator["label"], False, str(exc))

    def _list_custom_resources(
        self,
        group: str,
        version: str,
        namespace: str,
        plural: str,
    ) -> list[dict[str, Any]]:
        try:
            response = self._custom_api.list_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
            )
            return response.get("items", [])
        except ApiException as exc:
            if exc.status in (403, 404):
                return []
            raise
