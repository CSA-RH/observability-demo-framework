"""Kubernetes API access shared by the OpenShift services."""
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict

from kubernetes import client, config  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

log = logging.getLogger(__name__)

STORAGE_LABEL = {"observability-demo-framework": "storage"}
AGENT_SELECTOR = "observability-demo-framework=agent"


@dataclass
class KubeApis:
    core: Any
    apps: Any
    custom: Any
    batch: Any
    coordination: Any


def load_kube_apis() -> KubeApis:
    """In-cluster service account, or the local kubeconfig when running outside the cluster."""
    try:
        config.load_incluster_config()
        log.info("Running in-cluster. Service account loaded.")
    except config.ConfigException:
        config.load_kube_config()
        log.info("Running out-of-cluster. Local kubeconfig loaded.")
    return KubeApis(
        core=client.CoreV1Api(),
        apps=client.AppsV1Api(),
        custom=client.CustomObjectsApi(),
        batch=client.BatchV1Api(),
        coordination=client.CoordinationV1Api(),
    )


def current_namespace(context: str | None = None) -> str:
    """Namespace of the service account, or of the kubeconfig context outside the cluster."""
    ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    if os.path.exists(ns_path):
        with open(ns_path) as f:
            return f.read().strip()
    try:
        contexts, active_context = config.list_kube_config_contexts()
        if context is None:
            return active_context["context"]["namespace"]
        selected_context = next(ctx for ctx in contexts if ctx["name"] == context)
        return selected_context["context"]["namespace"]
    except (KeyError, StopIteration):
        return "default"


def create_or_replace(create: Callable, replace: Callable, namespace: str, name: str, body: Any, kind: str):
    """Create a namespaced object, replacing it if it already exists."""
    try:
        create(namespace=namespace, body=body)
        log.info(f"{kind} {name} created successfully.")
    except ApiException as e:
        if e.status != 409:
            log.error(f"Error creating {kind} {name}: {e}")
            raise
        replace(name=name, namespace=namespace, body=body)
        log.info(f"{kind} {name} replaced successfully.")


def ignore_not_found(action: Callable, description: str, namespace: str):
    """Run a delete; a missing object is not an error."""
    try:
        action()
        log.info(f"{description} deleted successfully.")
    except ApiException as e:
        if e.status != 404:
            log.error(f"Failed to delete {description}: {e}")
            raise
        log.warning(f"{description} not found in namespace '{namespace}'. Skipping.")


class ConfigMapJson:
    """JSON documents stored under one key of a labelled ConfigMap."""

    def __init__(self, core_api):
        self._core = core_api

    def load(self, name: str, key: str, namespace: str, default: Any = None) -> Any:
        """Parsed document; `default` (an empty list unless given) if the ConfigMap is missing."""
        try:
            configmap = self._core.read_namespaced_config_map(name, namespace)
        except ApiException as e:
            if e.status == 404:
                log.warning(f"ConfigMap '{name}' not found in namespace '{namespace}'.")
                return [] if default is None else default
            raise
        return json.loads((configmap.data or {}).get(key, "{}"))

    def save(self, name: str, key: str, namespace: str, document: Any) -> None:
        body: Dict[str, Any] = {
            "metadata": {"name": name, "namespace": namespace, "labels": dict(STORAGE_LABEL)},
            "data": {key: json.dumps(document)},
        }
        try:
            self._core.read_namespaced_config_map(name, namespace)
        except ApiException as e:
            if e.status != 404:
                raise
            self._core.create_namespaced_config_map(namespace, body)
            log.info(f"Created ConfigMap '{name}' in namespace '{namespace}'.")
            return
        self._core.patch_namespaced_config_map(name, namespace, body)
        log.info(f"Updated ConfigMap '{name}' in namespace '{namespace}'.")


ROUTE_API = {"group": "route.openshift.io", "version": "v1", "plural": "routes"}


def create_route(custom_api, namespace: str, name: str, service: str) -> None:
    """Edge-terminated Route to a Service. Existing Routes are kept; errors are only logged."""
    body = {
        "apiVersion": "route.openshift.io/v1",
        "kind": "Route",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"to": {"kind": "Service", "name": service}, "tls": {"termination": "edge"}},
    }
    try:
        custom_api.create_namespaced_custom_object(namespace=namespace, body=body, **ROUTE_API)
        log.info(f"Successfully created Route '{name}'.")
    except ApiException as e:
        if e.status == 409:
            log.warning(f"Route '{name}' already exists. Skipping.")
        else:
            log.error(f"Error creating Route '{name}': {e.reason}. Details: {e.body}")
    except Exception as e:
        log.error(f"An unexpected error occurred for Route '{name}': {e}")


def delete_route(custom_api, namespace: str, name: str) -> None:
    """Errors are only logged: a leftover Route must not block a simulation delete."""
    try:
        custom_api.delete_namespaced_custom_object(
            namespace=namespace, name=name, body=client.V1DeleteOptions(), **ROUTE_API)
        log.info(f"Successfully deleted Route '{name}'.")
    except ApiException as e:
        if e.status == 404:
            log.warning(f"Route '{name}' does not exist. Skipping.")
        else:
            log.error(f"Error deleting Route '{name}': {e.reason}. Details: {e.body}")
    except Exception as e:
        log.error(f"An unexpected error occurred for Route '{name}': {e}")


def route_url(custom_api, namespace: str, selector: str) -> str | None:
    """URL of the first Route matching the label selector, or None."""
    routes = custom_api.list_namespaced_custom_object(namespace=namespace, label_selector=selector, **ROUTE_API)
    for route in routes.get("items", []):
        spec = route.get("spec", {})
        scheme = "https" if spec.get("tls") else "http"
        return f"{scheme}://{spec.get('host')}"
    return None


def namespace_label(core_api, namespace: str, key: str) -> str | None:
    try:
        labels = core_api.read_namespace(name=namespace).metadata.labels or {}
    except ApiException as e:
        log.error(f"Error reading namespace '{namespace}': {e}")
        return None
    return labels.get(key)
