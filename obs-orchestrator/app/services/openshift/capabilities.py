import logging
from typing import Any, Dict

from kubernetes import config  # type: ignore

from services.interfaces import CapabilityService, TenantService
from services.openshift.kube import KubeApis, route_url
from settings import NamespaceLayout, Settings

log = logging.getLogger(__name__)

ADMIN_USER = "admin"


class OpenShiftCapabilityService(CapabilityService):
    """Cluster identity and links for the console. Phase 4 adds operator/UWM detection here."""

    def __init__(self, apis: KubeApis, layout: NamespaceLayout, settings: Settings, tenants: TenantService):
        self._custom = apis.custom
        self._layout = layout
        self._settings = settings
        self._tenants = tenants

    def _visible_users(self, user: str):
        users = [{k: v for k, v in u.items() if k != "password"} for u in self._tenants.get_users()]
        if user == ADMIN_USER:
            return users
        return [next((u for u in users if u.get("username") == user), None)]

    def get_cluster_info(self, user: str) -> Dict[str, Any]:
        app_namespace = self._layout.app_namespace
        user_namespace = app_namespace if user == ADMIN_USER else self._layout.user_namespace(user)
        users = self._visible_users(user)
        try:
            console = self._custom.get_cluster_custom_object(
                group="config.openshift.io", version="v1", plural="consoles", name="cluster")
            console_url = console["status"]["consoleURL"]
        except (config.ConfigException, KeyError):
            return {"Connected": False}

        gateway_url = route_url(self._custom, app_namespace, "app.kubernetes.io/component=gateway")
        return {
            "Connected": True,
            "Name": console_url.split(".")[2],  # https://console-openshift-console.apps.<cluster>.<domain>
            "Namespace": user_namespace,
            "AppNamespace": app_namespace,
            "UserNamespacePrefix": self._layout.user_namespace_prefix,
            "ConsoleURL": console_url,
            "apiLogsURL": f"{console_url}/k8s/ns/{app_namespace}/pods/{self._settings.hostname}/logs",
            "JaegerUI": f"{gateway_url}/obsdemo" if gateway_url else None,
            "GrafanaURL": route_url(self._custom, app_namespace, "observability-demo-framework=grafana"),
            "Users": users,
        }
