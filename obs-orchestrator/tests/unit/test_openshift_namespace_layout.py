"""OpenShiftClusterConnector builds namespaces and image references from the settings.

The Kubernetes API clients are MagicMocks: these tests only look at the names the connector
sends to the cluster, not at cluster behaviour.
"""
from unittest.mock import MagicMock

import pytest

import cluster_connector.OpenShiftClusterConnector as occ
from settings import Settings

AGENT = {"id": "cook-1", "type": "cook", "nextHop": []}


@pytest.fixture
def make_connector(monkeypatch):
    def factory(**env):
        for name in ("APP_NAMESPACE", "USER_NAMESPACE_PREFIX", "IMAGE_REGISTRY", "IMAGE_NAMESPACE", "KEYCLOAK_ISSUER"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        monkeypatch.setattr(occ, "settings", Settings())
        monkeypatch.setattr(occ.config, "load_incluster_config", lambda: None)
        apis = {}
        for api in ("CoreV1Api", "AppsV1Api", "CustomObjectsApi", "BatchV1Api", "CoordinationV1Api"):
            apis[api] = MagicMock(name=api)
            monkeypatch.setattr(occ.client, api, lambda api=api: apis[api])
        connector = occ.OpenShiftClusterConnector()
        # Without APP_NAMESPACE the connector falls back to its own namespace (service account file).
        connector._OpenShiftClusterConnector__layout._detect_namespace = lambda: "obs-demo"
        return connector, apis
    return factory


def deployment_call(apis):
    kwargs = apis["AppsV1Api"].create_namespaced_deployment.call_args.kwargs
    return kwargs["namespace"], kwargs["body"]["spec"]["template"]["spec"]["containers"][0]["image"]


def sync_job(connector, apis, monkeypatch):
    monkeypatch.setattr(connector, "_OpenShiftClusterConnector__wait_for_job_completion", lambda *a, **k: True)
    connector._OpenShiftClusterConnector__run_sync_users_job()
    kwargs = apis["BatchV1Api"].create_namespaced_job.call_args.kwargs
    container = kwargs["body"]["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e.get("value") for e in container["env"]}
    return kwargs["namespace"], container["image"], env


def test_default_layout_is_unchanged(make_connector, monkeypatch):
    connector, apis = make_connector()
    connector.create_simulation_resources("abc", [AGENT], "user-workload")
    namespace, image = deployment_call(apis)
    assert namespace == "obs-demo-abc"
    assert image.startswith("image-registry.openshift-image-registry.svc:5000/obs-demo/")

    job_namespace, job_image, env = sync_job(connector, apis, monkeypatch)
    assert job_namespace == "obs-demo"
    assert job_image == "image-registry.openshift-image-registry.svc:5000/obs-demo/obs-sync-users"
    assert env["APP_NAMESPACE"] == "obs-demo"
    assert env["USER_NAMESPACE_PREFIX"] == "obs-demo-"


def test_configured_layout(make_connector, monkeypatch):
    connector, apis = make_connector(APP_NAMESPACE="obs-lab", USER_NAMESPACE_PREFIX="obs-usr-",
                                     IMAGE_REGISTRY="quay.io", IMAGE_NAMESPACE="csa-rh")
    connector.create_simulation_resources("abc", [AGENT], "user-workload")
    namespace, image = deployment_call(apis)
    assert namespace == "obs-usr-abc"
    assert image.startswith("quay.io/csa-rh/")

    job_namespace, job_image, env = sync_job(connector, apis, monkeypatch)
    assert job_namespace == "obs-lab"
    assert job_image == "quay.io/csa-rh/obs-sync-users"
    assert env["APP_NAMESPACE"] == "obs-lab"
    assert env["USER_NAMESPACE_PREFIX"] == "obs-usr-"


def test_sync_skipped_only_for_local_keycloak(make_connector, monkeypatch):
    connector, apis = make_connector(KEYCLOAK_ISSUER="https://localhost:8443/realms/csa")
    assert connector.sync_users() is True
    apis["BatchV1Api"].create_namespaced_job.assert_not_called()
