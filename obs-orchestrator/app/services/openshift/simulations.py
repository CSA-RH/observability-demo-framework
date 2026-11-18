import base64
import json
import logging
import time
from typing import Any, Dict, List

from kubernetes import client  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from services.interfaces import MonitoringService, SimulationService
from services.openshift.kube import AGENT_SELECTOR, STORAGE_LABEL, KubeApis, create_or_replace, ignore_not_found
from settings import NamespaceLayout

log = logging.getLogger(__name__)

STATE_SECRET = "obs-demo-fw-state"
AGENT_PORT = 8080
METRICS_PORT = 8081

# Agent type -> (image, OpenTelemetry auto-instrumentation annotation). Anything else is Node.js.
AGENT_RUNTIMES = {
    "waiter": ("obs-client-dotnet:latest", "instrumentation.opentelemetry.io/inject-dotnet"),
}
DEFAULT_RUNTIME = ("obs-client-node:latest", "instrumentation.opentelemetry.io/inject-nodejs")
INSTRUMENTATION = "obs-otel/instrumentation"
AGENT_CONTAINER = "core"
IMAGE_TRIGGER_ANNOTATION = "image.openshift.io/triggers"


class OpenShiftSimulationService(SimulationService):
    """Agents are a Deployment + Service each in the user namespace; the simulation definition is
    stored in a Secret there. Monitoring resources are delegated to the MonitoringService."""

    def __init__(self, apis: KubeApis, layout: NamespaceLayout, monitoring: MonitoringService,
                 ready_timeout: float = 300, poll_interval: float = 5):
        self._core = apis.core
        self._apps = apis.apps
        self._layout = layout
        self._monitoring = monitoring
        self._ready_timeout = ready_timeout
        self._poll_interval = poll_interval

    # --- manifests -----------------------------------------------------------------------------

    def _image_trigger(self, image: str) -> Dict[str, str]:
        """With in-cluster builds, a new image (or re-applying the Deployment) rolls the agent out
        with the current digest of the ImageStreamTag. External registries: no trigger."""
        if not self._layout.uses_internal_registry:
            return {}
        trigger = {
            "from": {"kind": "ImageStreamTag", "name": image, "namespace": self._layout.image_namespace},
            "fieldPath": f'spec.template.spec.containers[?(@.name=="{AGENT_CONTAINER}")].image',
        }
        return {IMAGE_TRIGGER_ANNOTATION: json.dumps([trigger])}

    def deployment_manifest(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        image, inject_annotation = AGENT_RUNTIMES.get(agent["type"], DEFAULT_RUNTIME)
        labels = {"app": agent["id"], "observability-demo-framework": "agent"}
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": agent["id"], "labels": labels, "annotations": self._image_trigger(image)},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": agent["id"]}},
                "template": {
                    "metadata": {"labels": labels, "annotations": {inject_annotation: INSTRUMENTATION}},
                    "spec": {
                        "containers": [{
                            "name": AGENT_CONTAINER,
                            "image": self._layout.image(image),
                            "ports": [{"containerPort": AGENT_PORT}],
                            "env": [{"name": "TARGETS", "value": ",".join(agent.get("nextHop", []))}],
                            "readinessProbe": {
                                "httpGet": {"path": "/", "port": AGENT_PORT},
                                "initialDelaySeconds": 3,
                                "periodSeconds": 3,
                            },
                        }],
                    },
                },
            },
        }

    @staticmethod
    def service_manifest(agent: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": agent["id"], "labels": {"app": agent["id"], "observability-demo-framework": "agent"}},
            "spec": {
                "selector": {"app": agent["id"]},
                "ports": [
                    {"protocol": "TCP", "port": AGENT_PORT, "targetPort": AGENT_PORT, "name": "api"},
                    {"protocol": "TCP", "port": METRICS_PORT, "targetPort": METRICS_PORT, "name": "metrics"},
                ],
            },
        }

    # --- lifecycle -----------------------------------------------------------------------------

    def create_resources(self, user: str, agents: List[Dict[str, Any]], stack: str) -> List[Dict[str, Any]]:
        namespace = self._layout.user_namespace(user)
        self._monitoring.create_monitoring_stack(user, stack)
        for agent in agents:
            log.info(f"Agent: {agent['id']} (type {agent['type']})")
            create_or_replace(self._apps.create_namespaced_deployment, self._apps.replace_namespaced_deployment,
                              namespace, agent["id"], self.deployment_manifest(agent), "Deployment")
            create_or_replace(self._core.create_namespaced_service, self._core.replace_namespaced_service,
                              namespace, agent["id"], self.service_manifest(agent), "Service")
            self._monitoring.create_service_monitor(user, agent["id"], stack)

        # Wait for every agent before returning: the console connects them right after.
        for agent in agents:
            if not self._wait_for_service_ip(namespace, agent["id"]):
                log.error(f"Failed to retrieve the Service IP address for {agent['id']}.")
                continue
            agent["dns"] = self.agent_hostname(user, agent["id"])
            agent["port"] = AGENT_PORT
            self._wait_for_deployment_ready(namespace, agent["id"])
        log.debug(agents)
        return agents

    def save(self, user: str, simulation: Dict[str, Any]) -> None:
        namespace = self._layout.user_namespace(user)
        encoded = base64.b64encode(json.dumps(simulation).encode("utf-8")).decode("utf-8")
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=STATE_SECRET, labels=dict(STORAGE_LABEL)),
            data={"simulation": encoded},
        )
        create_or_replace(self._core.create_namespaced_secret, self._core.replace_namespaced_secret,
                          namespace, STATE_SECRET, secret, "Simulation Secret")

    def get(self, user: str) -> Dict[str, Any]:
        namespace = self._layout.user_namespace(user)
        try:
            secret = self._core.read_namespaced_secret(STATE_SECRET, namespace)
        except ApiException as e:
            if e.status == 404:
                log.warning(f"Secret '{STATE_SECRET}' not found in namespace '{namespace}'.")
                return {}
            raise RuntimeError(f"Failed to read Secret '{STATE_SECRET}': {e}")
        if "simulation" not in (secret.data or {}):
            raise RuntimeError(f"Secret '{STATE_SECRET}' does not contain the 'simulation' key.")
        simulation = json.loads(base64.b64decode(secret.data["simulation"]).decode("utf-8"))

        pods = self._agent_pods(namespace)
        for agent in simulation["agents"]:
            agent["pod"] = pods.get(agent["id"])  # None while the pod is being (re)created
        return simulation

    def delete(self, user: str) -> None:
        namespace = self._layout.user_namespace(user)
        for deployment in self._apps.list_namespaced_deployment(namespace=namespace, label_selector=AGENT_SELECTOR).items:
            log.info(f"Deleting Deployment: {deployment.metadata.name}")
            self._apps.delete_namespaced_deployment(name=deployment.metadata.name, namespace=namespace)
        for service in self._core.list_namespaced_service(namespace=namespace, label_selector=AGENT_SELECTOR).items:
            log.info(f"Deleting Service: {service.metadata.name}")
            self._core.delete_namespaced_service(name=service.metadata.name, namespace=namespace)

        self._monitoring.delete_monitoring(user)

        ignore_not_found(lambda: self._core.delete_namespaced_secret(STATE_SECRET, namespace),
                         f"Secret '{STATE_SECRET}'", namespace)
        log.info("All matching resources deleted successfully.")

    def agent_hostname(self, user: str, agent_id: str) -> str:
        return f"{agent_id}.{self._layout.user_namespace(user)}.svc"

    # --- helpers -------------------------------------------------------------------------------

    def _agent_pods(self, namespace: str) -> Dict[str, str]:
        """Deployment name -> pod name (`<deployment>-<replicaset hash>-<pod hash>`)."""
        pods = self._core.list_namespaced_pod(namespace, label_selector=AGENT_SELECTOR)
        return {"-".join(pod.metadata.name.split("-")[:-2]): pod.metadata.name for pod in pods.items}

    def _wait_for_service_ip(self, namespace: str, name: str) -> str | None:
        deadline = time.monotonic() + self._ready_timeout
        while True:
            service = self._core.read_namespaced_service(name=name, namespace=namespace)
            if service.spec.cluster_ip:
                log.info(f"Service {name} IP: {service.spec.cluster_ip}")
                return service.spec.cluster_ip
            if time.monotonic() >= deadline:
                log.info(f"Timeout waiting for Service {name} to be ready.")
                return None
            time.sleep(self._poll_interval)

    def _wait_for_deployment_ready(self, namespace: str, name: str) -> bool:
        deadline = time.monotonic() + self._ready_timeout
        while True:
            deployment = self._apps.read_namespaced_deployment(name=name, namespace=namespace)
            ready, desired = deployment.status.ready_replicas, deployment.spec.replicas
            if ready == desired:
                log.info(f"All pods for deployment '{name}' are ready.")
                return True
            if time.monotonic() >= deadline:
                log.info(f"Timeout: not all pods for deployment '{name}' are ready after {self._ready_timeout} seconds.")
                return False
            log.info(f"Waiting for pods of deployment {name}. Ready pods: {ready}/{desired}")
            time.sleep(self._poll_interval)
