"""OpenShift domain services against the in-memory Kubernetes API (`fake_kube`)."""
import base64
import contextlib
import json

import pytest
from kubernetes.client.rest import ApiException  # type: ignore

import services.openshift.tenants as tenants_module
from fake_kube import fake_kube_apis
from operations.lease_lock import LeaseLockError
from services import build_openshift_services
from services.openshift.monitoring import ALERTS_CONFIGMAP, COO_GROUP, UWM_GROUP
from services.openshift.simulations import STATE_SECRET
from settings import Settings

USER = "abc"
AGENTS = [
    {"id": "customer-1", "type": "customer", "nextHop": ["waiter-1"]},
    {"id": "waiter-1", "type": "waiter"},
]


@pytest.fixture
def make_services(monkeypatch):
    def factory(stack="user-workload", **env):
        for name in ("APP_NAMESPACE", "USER_NAMESPACE_PREFIX", "IMAGE_REGISTRY", "IMAGE_NAMESPACE",
                     "KEYCLOAK_ISSUER", "HOSTNAME"):
            monkeypatch.delenv(name, raising=False)
        env.setdefault("APP_NAMESPACE", "obs-demo")
        for name, value in env.items():
            if value is not None:  # None: leave unset
                monkeypatch.setenv(name, value)
        apis = fake_kube_apis()
        services = build_openshift_services(Settings(), apis)
        for service in (services.tenants, services.simulations):
            service._poll_interval = 0
        user_namespace = services.simulations._layout.user_namespace(USER)
        apis.core.add_namespace(user_namespace, {"observability-stack": stack})
        return services, apis, user_namespace
    return factory


@pytest.fixture
def no_lease(monkeypatch):
    monkeypatch.setattr(tenants_module, "user_sync_lease", lambda *a: contextlib.nullcontext())


def agents():
    return [dict(a) for a in AGENTS]


# --- namespace layout ------------------------------------------------------------------------------

def deployment_image(apis, namespace, name="customer-1"):
    return apis.apps.deployments.get(namespace, name)["spec"]["template"]["spec"]["containers"][0]["image"]


def sync_job(apis, namespace):
    (job,) = apis.batch.jobs.list(namespace)
    container = job["spec"]["template"]["spec"]["containers"][0]
    return container["image"], {e["name"]: e.get("value") for e in container["env"]}


def test_default_layout_is_unchanged(make_services, monkeypatch, no_lease):
    # Without APP_NAMESPACE the app namespace is the orchestrator's own (service account file).
    monkeypatch.setattr("services.openshift.kube.current_namespace", lambda: "obs-demo")
    services, apis, namespace = make_services(APP_NAMESPACE=None)
    assert namespace == "obs-demo-abc"
    services.simulations.create_resources(USER, agents(), "user-workload")
    assert deployment_image(apis, namespace).startswith("image-registry.openshift-image-registry.svc:5000/obs-demo/")

    assert services.tenants.sync_users() is True
    image, env = sync_job(apis, "obs-demo")
    assert image == "image-registry.openshift-image-registry.svc:5000/obs-demo/obs-sync-users"
    assert env["APP_NAMESPACE"] == "obs-demo"
    assert env["USER_NAMESPACE_PREFIX"] == "obs-demo-"


def test_configured_layout(make_services, no_lease):
    services, apis, namespace = make_services(APP_NAMESPACE="obs-lab", USER_NAMESPACE_PREFIX="obs-usr-",
                                              IMAGE_REGISTRY="quay.io", IMAGE_NAMESPACE="csa-rh")
    assert namespace == "obs-usr-abc"
    services.simulations.create_resources(USER, agents(), "user-workload")
    assert deployment_image(apis, namespace).startswith("quay.io/csa-rh/")

    assert services.tenants.sync_users() is True
    image, env = sync_job(apis, "obs-lab")
    assert image == "quay.io/csa-rh/obs-sync-users"
    assert env["APP_NAMESPACE"] == "obs-lab"
    assert env["USER_NAMESPACE_PREFIX"] == "obs-usr-"


# --- tenants --------------------------------------------------------------------------------------

def test_users_round_trip_through_configmap(make_services):
    services, apis, _ = make_services()
    assert services.tenants.get_users() == []
    services.tenants.save_users([{"username": "abc"}])
    services.tenants.save_users([{"username": "abc"}, {"username": "def"}])
    assert services.tenants.get_users() == [{"username": "abc"}, {"username": "def"}]
    configmap = apis.core.configmaps.get("obs-demo", "obs-demo-fwk-users")
    assert configmap["metadata"]["labels"] == {"observability-demo-framework": "storage"}


def test_sync_skipped_only_for_local_keycloak(make_services):
    services, apis, _ = make_services(KEYCLOAK_ISSUER="https://localhost:8443/realms/csa")
    assert services.tenants.sync_users() is True
    assert apis.batch.jobs.list("obs-demo") == []


@pytest.mark.parametrize("outcome, expected", [("Complete", True), ("Failed", False)])
def test_sync_reports_job_outcome(make_services, no_lease, outcome, expected):
    services, apis, _ = make_services()
    apis.batch.outcome = outcome
    assert services.tenants.sync_users() is expected


def test_sync_times_out(make_services, no_lease):
    services, apis, _ = make_services()
    apis.batch.outcome = None
    services.tenants._job_timeout = 0.01
    assert services.tenants.sync_users() is False


@pytest.mark.parametrize("error", [ApiException(status=403), LeaseLockError("busy")])
def test_sync_runs_without_lock_when_lease_unavailable(make_services, monkeypatch, error):
    services, apis, _ = make_services()

    def lease(*args):
        raise error
    monkeypatch.setattr(tenants_module, "user_sync_lease", lease)
    assert services.tenants.sync_users() is True
    assert len(apis.batch.jobs.list("obs-demo")) == 1


def test_sync_propagates_other_lease_errors(make_services, monkeypatch):
    services, _, _ = make_services()

    def lease(*args):
        raise ApiException(status=500)
    monkeypatch.setattr(tenants_module, "user_sync_lease", lease)
    with pytest.raises(ApiException):
        services.tenants.sync_users()


# --- simulations ----------------------------------------------------------------------------------

def test_create_user_workload_simulation(make_services):
    services, apis, ns = make_services()
    result = services.simulations.create_resources(USER, agents(), "user-workload")

    assert [a["dns"] for a in result] == [f"customer-1.{ns}.svc", f"waiter-1.{ns}.svc"]
    assert all(a["port"] == 8080 for a in result)
    assert apis.apps.deployments.names(ns) == ["customer-1", "waiter-1"]
    assert apis.core.services.names(ns) == ["customer-1", "waiter-1"]
    assert apis.custom.store(UWM_GROUP, "servicemonitors").names(ns) == ["customer-1", "waiter-1"]
    assert apis.custom.store(COO_GROUP, "monitoringstacks").names(ns) == []

    customer = apis.apps.deployments.get(ns, "customer-1")["spec"]["template"]
    waiter = apis.apps.deployments.get(ns, "waiter-1")["spec"]["template"]
    assert customer["spec"]["containers"][0]["env"] == [{"name": "TARGETS", "value": "waiter-1"}]
    assert waiter["spec"]["containers"][0]["env"] == [{"name": "TARGETS", "value": ""}]
    assert customer["metadata"]["annotations"] == {
        "instrumentation.opentelemetry.io/inject-nodejs": "obs-otel/instrumentation"}
    assert waiter["metadata"]["annotations"] == {
        "instrumentation.opentelemetry.io/inject-dotnet": "obs-otel/instrumentation"}
    assert waiter["spec"]["containers"][0]["image"].endswith("/obs-client-dotnet:latest")


def test_create_coo_simulation(make_services):
    services, apis, ns = make_services(stack="coo")
    services.simulations.create_resources(USER, agents(), "coo")

    (stack,) = apis.custom.store(COO_GROUP, "monitoringstacks").list(ns)
    assert stack["metadata"]["name"] == f"monitoring-stack-{USER}"
    assert stack["spec"]["resourceSelector"] == {"matchLabels": {"monitoring-stack": USER}}
    monitors = apis.custom.store(COO_GROUP, "servicemonitors").list(ns)
    assert {m["metadata"]["labels"]["monitoring-stack"] for m in monitors} == {USER}
    assert apis.custom.store(UWM_GROUP, "servicemonitors").names(ns) == []
    routes = apis.custom.store("route.openshift.io", "routes")
    assert routes.names(ns) == [f"alertmanager-{USER}", f"prometheus-{USER}"]
    assert routes.get(ns, f"prometheus-{USER}")["spec"]["to"]["name"] == f"monitoring-stack-{USER}-prometheus"


def test_recreating_a_simulation_replaces_workloads(make_services):
    services, apis, ns = make_services()
    services.simulations.create_resources(USER, agents(), "user-workload")
    changed = agents()
    changed[0]["nextHop"] = []
    apis.custom.stores.clear()  # ServiceMonitors are not replaced, only created
    services.simulations.create_resources(USER, changed, "user-workload")
    env = apis.apps.deployments.get(ns, "customer-1")["spec"]["template"]["spec"]["containers"][0]["env"]
    assert env == [{"name": "TARGETS", "value": ""}]
    assert apis.core.services.get(ns, "customer-1")["spec"]["clusterIP"]


def test_agents_without_service_ip_get_no_dns(make_services):
    services, apis, _ = make_services()
    apis.core.assign_cluster_ip = False
    services.simulations._ready_timeout = 0
    result = services.simulations.create_resources(USER, agents(), "user-workload")
    assert all("dns" not in a for a in result)


def test_waits_for_unready_deployments_until_timeout(make_services):
    services, apis, ns = make_services()
    apis.apps.ready = False
    services.simulations._ready_timeout = 0.01
    result = services.simulations.create_resources(USER, agents(), "user-workload")
    assert result[0]["dns"] == f"customer-1.{ns}.svc"


def test_simulation_round_trip_adds_pod_names(make_services):
    services, apis, ns = make_services()
    assert services.simulations.get(USER) == {}
    services.simulations.create_resources(USER, agents(), "user-workload")
    services.simulations.save(USER, {"agents": agents(), "layout": []})
    services.simulations.save(USER, {"agents": agents(), "layout": [{"id": "x"}]})  # replaces

    secret = apis.core.secrets.get(ns, STATE_SECRET)
    assert json.loads(base64.b64decode(secret["data"]["simulation"]))["layout"] == [{"id": "x"}]
    simulation = services.simulations.get(USER)
    assert [a["pod"] for a in simulation["agents"]] == ["customer-1-5d9c7b8f4d-x2k9p", "waiter-1-5d9c7b8f4d-x2k9p"]


def test_missing_pod_does_not_break_get(make_services):
    services, apis, ns = make_services()
    services.simulations.save(USER, {"agents": agents()})
    assert [a["pod"] for a in services.simulations.get(USER)["agents"]] == [None, None]


def test_secret_without_simulation_key_is_an_error(make_services):
    services, apis, ns = make_services()
    apis.core.create_namespaced_secret(ns, {"metadata": {"name": STATE_SECRET}, "data": {}})
    with pytest.raises(RuntimeError):
        services.simulations.get(USER)


@pytest.mark.parametrize("stack", ["user-workload", "coo"])
def test_delete_simulation_removes_everything(make_services, stack):
    services, apis, ns = make_services(stack=stack)
    services.simulations.create_resources(USER, agents(), stack)
    services.simulations.save(USER, {"agents": agents()})
    services.monitoring.create_alert(USER, stack, "rule-1", "High", "critical", "g", "up == 0", "s")
    services.monitoring.save_alert_definition(USER, {"id": "rule-1"})

    services.simulations.delete(USER)

    assert apis.apps.deployments.names(ns) == []
    assert apis.core.services.names(ns) == []
    assert apis.core.pods.names(ns) == []
    assert apis.core.secrets.names(ns) == []
    assert apis.core.configmaps.names(ns) == []
    for store in apis.custom.stores.values():
        assert store.names(ns) == [], store.kind


def test_delete_empty_simulation_is_a_no_op(make_services):
    services, _, _ = make_services(stack="coo")
    services.simulations.delete(USER)  # no MonitoringStack, Routes, Secret or alerts: nothing raises


# --- alerts ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("stack, group", [("user-workload", UWM_GROUP), ("coo", COO_GROUP)])
def test_alert_lifecycle(make_services, stack, group):
    services, apis, ns = make_services(stack=stack)
    monitoring = services.monitoring
    assert monitoring.create_alert(USER, stack, "rule-1", "High", "critical", "grp", "up == 0", "down") == {"success": True}
    rule = apis.custom.store(group, "prometheusrules").get(ns, "rule-1")
    assert rule["spec"]["groups"][0]["rules"][0]["expr"] == "up == 0"
    assert ("monitoring-stack" in rule["metadata"]["labels"]) == (stack == "coo")
    assert monitoring.create_alert(USER, stack, "rule-1", "High", "critical", "grp", "up == 0", "down") is None

    monitoring.save_alert_definition(USER, {"id": "rule-1"})
    monitoring.save_alert_definition(USER, {"id": "rule-2"})
    assert monitoring.get_alert_definitions(USER) == [{"id": "rule-1"}, {"id": "rule-2"}]
    assert monitoring.delete_alert_definition(USER, "rule-1") == {"success": True}
    assert monitoring.get_alert_definitions(USER) == [{"id": "rule-2"}]

    assert monitoring.delete_alert(USER, "rule-1") == {"success": True}
    missing = monitoring.delete_alert(USER, "rule-1")
    assert missing["success"] is False and missing["error"].status == 404


def test_alert_definitions_are_per_user_namespace(make_services):
    services, apis, ns = make_services()
    services.monitoring.save_alert_definition(USER, {"id": "rule-1"})
    assert apis.core.configmaps.names(ns) == [ALERTS_CONFIGMAP]
    assert services.monitoring.get_alert_definitions("someone-else") == []


# --- operations -----------------------------------------------------------------------------------

def test_operations_round_trip(make_services):
    services, apis, _ = make_services()
    store = services.operations
    assert store.get("missing") is None
    op = store.create("user-create", {"username": "abc"})
    store.update(op, status="failed", error="boom", result=[1], metadata={"m": 1})
    operation = store.get(op)
    assert (operation["status"], operation["error"], operation["result"], operation["metadata"]) == \
        ("failed", "boom", [1], {"m": 1})
    assert apis.core.configmaps.names("obs-demo") == ["obs-demo-fwk-operations"]
    with pytest.raises(KeyError):
        store.update("missing", status="running")


# --- capabilities ---------------------------------------------------------------------------------

def add_console(apis):
    apis.custom.cluster_objects[("config.openshift.io", "consoles", "cluster")] = {
        "status": {"consoleURL": "https://console-openshift-console.apps.mycluster.example.com"}}


def test_cluster_info_for_user(make_services, monkeypatch):
    services, apis, ns = make_services(HOSTNAME="obs-orchestrator-abc")
    add_console(apis)
    services.tenants.save_users([{"username": "abc", "password": "x"}, {"username": "def", "password": "y"}])

    info = services.capabilities.get_cluster_info(USER)
    assert info["Connected"] is True
    assert info["Name"] == "mycluster"
    assert info["Namespace"] == ns
    assert info["AppNamespace"] == "obs-demo"
    assert info["UserNamespacePrefix"] == "obs-demo-"
    assert info["apiLogsURL"].endswith("/k8s/ns/obs-demo/pods/obs-orchestrator-abc/logs")
    assert info["Users"] == [{"username": "abc"}]
    assert info["JaegerUI"] is None and info["GrafanaURL"] is None
    assert services.tenants.get_users()[0]["password"] == "x"  # the registry is not modified


def test_cluster_info_for_admin_with_routes(make_services):
    services, apis, _ = make_services()
    add_console(apis)
    services.tenants.save_users([{"username": "abc", "password": "x"}])
    routes = apis.custom.store("route.openshift.io", "routes")
    routes.create("obs-demo", {"metadata": {"name": "gw", "labels": {"app.kubernetes.io/component": "gateway"}},
                               "spec": {"host": "tempo.example.com", "tls": {"termination": "edge"}}})
    routes.create("obs-demo", {"metadata": {"name": "grafana", "labels": {"observability-demo-framework": "grafana"}},
                               "spec": {"host": "grafana.example.com"}})

    info = services.capabilities.get_cluster_info("admin")
    assert info["Namespace"] == "obs-demo"
    assert info["Users"] == [{"username": "abc"}]
    assert info["JaegerUI"] == "https://tempo.example.com/obsdemo"
    assert info["GrafanaURL"] == "http://grafana.example.com"


def test_cluster_info_without_console(make_services):
    services, apis, _ = make_services()
    apis.custom.cluster_objects[("config.openshift.io", "consoles", "cluster")] = {"status": {}}
    assert services.capabilities.get_cluster_info(USER) == {"Connected": False}
