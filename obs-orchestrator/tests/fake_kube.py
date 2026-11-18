"""In-memory stand-in for the Kubernetes API clients used by `services.openshift`.

Only the calls the services make are implemented, with the API server behaviours they rely on:
404 on missing objects, 409 on duplicates, ClusterIPs assigned on Service creation, one ready pod
per Deployment, `generateName` for Jobs and equality label selectors. Objects are stored as plain
dicts (API field names) and returned as `kubernetes.client` models, like the real clients do.
"""
import copy
import secrets
from types import SimpleNamespace
from unittest.mock import MagicMock

from kubernetes import client  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

from services.openshift.kube import KubeApis

_api_client = client.ApiClient()


def _to_dict(body):
    return copy.deepcopy(_api_client.sanitize_for_serialization(body))


def _model(data, kind):
    return _api_client._ApiClient__deserialize(copy.deepcopy(data), kind)


def _matches(obj, selector):
    if not selector:
        return True
    labels = obj.get("metadata", {}).get("labels") or {}
    return all(labels.get(k) == v for k, v in (term.split("=", 1) for term in selector.split(",")))


class _Store:
    """Objects by (namespace, name) for one kind."""

    def __init__(self, kind):
        self.kind = kind
        self.objects = {}

    def get(self, namespace, name):
        try:
            return self.objects[(namespace, name)]
        except KeyError:
            raise ApiException(status=404, reason=f"{self.kind} {namespace}/{name} not found")

    def create(self, namespace, body):
        obj = _to_dict(body)
        obj.setdefault("metadata", {})
        name = obj["metadata"].get("name")
        if name is None:  # generateName
            name = obj["metadata"]["generateName"] + secrets.token_hex(3)
            obj["metadata"]["name"] = name
        obj["metadata"]["namespace"] = namespace
        if (namespace, name) in self.objects:
            raise ApiException(status=409, reason=f"{self.kind} {namespace}/{name} already exists")
        self.objects[(namespace, name)] = obj
        return obj

    def replace(self, namespace, name, body):
        self.get(namespace, name)
        obj = _to_dict(body)
        obj["metadata"]["namespace"] = namespace
        self.objects[(namespace, name)] = obj
        return obj

    def delete(self, namespace, name):
        self.get(namespace, name)
        del self.objects[(namespace, name)]

    def list(self, namespace, selector=None):
        return [o for (ns, _), o in self.objects.items() if ns == namespace and _matches(o, selector)]

    def names(self, namespace):
        return sorted(name for ns, name in self.objects if ns == namespace)


class FakeCoreV1:
    def __init__(self):
        self.configmaps = _Store("ConfigMap")
        self.secrets = _Store("Secret")
        self.services = _Store("Service")
        self.pods = _Store("Pod")
        self.namespaces = {}
        self.assign_cluster_ip = True

    # namespaces
    def add_namespace(self, name, labels=None):
        self.namespaces[name] = {"metadata": {"name": name, "labels": labels or {}}}

    def read_namespace(self, name):
        if name not in self.namespaces:
            raise ApiException(status=404, reason=f"Namespace {name} not found")
        return _model(self.namespaces[name], "V1Namespace")

    # configmaps
    def read_namespaced_config_map(self, name, namespace):
        return _model(self.configmaps.get(namespace, name), "V1ConfigMap")

    def create_namespaced_config_map(self, namespace, body):
        self.configmaps.create(namespace, body)

    def patch_namespaced_config_map(self, name, namespace, body):
        obj = self.configmaps.get(namespace, name)
        obj.setdefault("data", {}).update(_to_dict(body).get("data", {}))

    def delete_namespaced_config_map(self, name, namespace):
        self.configmaps.delete(namespace, name)

    # secrets
    def create_namespaced_secret(self, namespace, body):
        self.secrets.create(namespace, body)

    def replace_namespaced_secret(self, name, namespace, body):
        self.secrets.replace(namespace, name, body)

    def read_namespaced_secret(self, name, namespace):
        return _model(self.secrets.get(namespace, name), "V1Secret")

    def delete_namespaced_secret(self, name, namespace):
        self.secrets.delete(namespace, name)

    # services
    def create_namespaced_service(self, namespace, body):
        obj = self.services.create(namespace, body)
        if self.assign_cluster_ip:
            obj["spec"]["clusterIP"] = f"172.30.0.{len(self.services.objects)}"

    def replace_namespaced_service(self, name, namespace, body):
        ip = self.services.get(namespace, name)["spec"].get("clusterIP")
        self.services.replace(namespace, name, body)["spec"]["clusterIP"] = ip

    def read_namespaced_service(self, name, namespace):
        return _model(self.services.get(namespace, name), "V1Service")

    def list_namespaced_service(self, namespace, label_selector=None):
        return _model({"items": self.services.list(namespace, label_selector)}, "V1ServiceList")

    def delete_namespaced_service(self, name, namespace):
        self.services.delete(namespace, name)

    # pods
    def list_namespaced_pod(self, namespace, label_selector=None):
        return _model({"items": self.pods.list(namespace, label_selector)}, "V1PodList")


class FakeAppsV1:
    def __init__(self, core: FakeCoreV1):
        self._core = core
        self.deployments = _Store("Deployment")
        self.ready = True

    def _status(self, obj):
        replicas = obj["spec"].get("replicas", 1)
        obj["status"] = {"readyReplicas": replicas if self.ready else 0}

    def create_namespaced_deployment(self, namespace, body):
        obj = self.deployments.create(namespace, body)
        self._status(obj)
        name = obj["metadata"]["name"]
        labels = obj["spec"]["template"]["metadata"]["labels"]
        self._core.pods.create(namespace, {"metadata": {"name": f"{name}-5d9c7b8f4d-x2k9p", "labels": labels}})

    def replace_namespaced_deployment(self, name, namespace, body):
        self._status(self.deployments.replace(namespace, name, body))

    def read_namespaced_deployment(self, name, namespace):
        return _model(self.deployments.get(namespace, name), "V1Deployment")

    def list_namespaced_deployment(self, namespace, label_selector=None):
        return _model({"items": self.deployments.list(namespace, label_selector)}, "V1DeploymentList")

    def delete_namespaced_deployment(self, name, namespace):
        self.deployments.delete(namespace, name)
        for pod in self._core.pods.names(namespace):
            if pod.startswith(f"{name}-"):
                self._core.pods.delete(namespace, pod)


class FakeCustomObjects:
    """Custom resources keyed by (group, plural); the version is ignored."""

    def __init__(self):
        self.stores = {}
        self.cluster_objects = {}

    def store(self, group, plural):
        return self.stores.setdefault((group, plural), _Store(f"{plural}.{group}"))

    def create_namespaced_custom_object(self, group, version, namespace, plural, body):
        return self.store(group, plural).create(namespace, body)

    def list_namespaced_custom_object(self, group, version, namespace, plural, label_selector=None):
        return {"items": copy.deepcopy(self.store(group, plural).list(namespace, label_selector))}

    def delete_namespaced_custom_object(self, group, version, namespace, plural, name, body=None):
        self.store(group, plural).delete(namespace, name)

    def get_cluster_custom_object(self, group, version, plural, name):
        try:
            return copy.deepcopy(self.cluster_objects[(group, plural, name)])
        except KeyError:
            raise ApiException(status=404, reason=f"{plural}.{group} {name} not found")


class FakeBatchV1:
    def __init__(self):
        self.jobs = _Store("Job")
        self.outcome = "Complete"  # condition type reported for every Job; None = never finishes

    def create_namespaced_job(self, namespace, body):
        return _model(self.jobs.create(namespace, body), "V1Job")

    def read_namespaced_job_status(self, name, namespace):
        job = self.jobs.get(namespace, name)
        conditions = [{"type": self.outcome, "status": "True", "reason": "Test", "message": "fake"}] \
            if self.outcome else []
        return SimpleNamespace(status=SimpleNamespace(conditions=[SimpleNamespace(**c) for c in conditions]),
                               metadata=SimpleNamespace(name=job["metadata"]["name"]))


def fake_kube_apis() -> KubeApis:
    core = FakeCoreV1()
    return KubeApis(core=core, apps=FakeAppsV1(core), custom=FakeCustomObjects(), batch=FakeBatchV1(),
                    coordination=MagicMock(name="CoordinationV1Api"))
