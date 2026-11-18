import logging
import time
from typing import Any, Dict, List

from kubernetes.client.rest import ApiException  # type: ignore

from operations.lease_lock import LeaseLockError, user_sync_lease
from services.interfaces import TenantService
from services.openshift.kube import ConfigMapJson, KubeApis
from settings import NamespaceLayout, Settings

log = logging.getLogger(__name__)

USERS_CONFIGMAP = "obs-demo-fwk-users"
SYNC_SERVICE_ACCOUNT = "obs-sync-users"
SYNC_PLAYBOOK_CONFIGMAP = "sync-users-playbook"
IDP_CONFIGMAP = "idp-data"


class OpenShiftTenantService(TenantService):
    """User registry in a ConfigMap of the app namespace; applied by the `sync-users` Job.

    The Job runs an Ansible playbook that syncs Keycloak users and provisions each user's
    namespace, RoleBindings and image-puller bindings.
    """

    def __init__(self, apis: KubeApis, layout: NamespaceLayout, settings: Settings,
                 job_timeout: float = 300, poll_interval: float = 5):
        self._apis = apis
        self._layout = layout
        self._settings = settings
        self._store = ConfigMapJson(apis.core)
        self._job_timeout = job_timeout
        self._poll_interval = poll_interval

    def get_users(self) -> List[Dict[str, Any]]:
        return self._store.load(USERS_CONFIGMAP, "users", self._layout.app_namespace)

    def save_users(self, users: List[Dict[str, Any]]) -> None:
        self._store.save(USERS_CONFIGMAP, "users", self._layout.app_namespace, users)

    def sync_users(self) -> bool:
        if self._settings.is_local_keycloak:
            log.info("Local development mode: user registry updated in ConfigMap only. "
                     "Cluster Keycloak sync job skipped.")
            return True
        try:
            with user_sync_lease(self._apis.coordination, self._layout.app_namespace):
                return self._run_sync_job()
        except ApiException as exc:
            if exc.status != 403:
                raise
            log.warning("obs-orchestrator-sa cannot manage leases.coordination.k8s.io. "
                        "Running user sync without lock. "
                        "Apply obs-orchestrator/scripts/patch-rbac-leases.sh to fix RBAC.")
            return self._run_sync_job()
        except LeaseLockError as exc:
            log.warning(f"Could not acquire user-sync lease ({exc}). Running sync without lock.")
            return self._run_sync_job()

    def sync_job_manifest(self) -> Dict[str, Any]:
        def idp(key):
            return {"configMapKeyRef": {"name": IDP_CONFIGMAP, "key": key}}

        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "generateName": "sync-users-",
                "labels": {"observability-demo-framework": "users"},
            },
            "spec": {
                "template": {
                    "spec": {
                        "serviceAccountName": SYNC_SERVICE_ACCOUNT,
                        "containers": [{
                            "name": "ansible",
                            "image": self._layout.image("obs-sync-users"),
                            "command": ["ansible-playbook", "/runner/playbook-sync-users.yml"],
                            "env": [
                                {"name": "APP_NAMESPACE", "value": self._layout.app_namespace},
                                {"name": "USER_NAMESPACE_PREFIX", "value": self._layout.user_namespace_prefix},
                                {"name": "KC_API_URL", "valueFrom": idp("endpoint")},
                                {"name": "KC_API_CLIENT_ID", "valueFrom": idp("client_id")},
                                {"name": "KC_API_CLIENT_SECRET", "valueFrom": idp("client_secret")},
                                {"name": "KC_API_REALM", "valueFrom": idp("realm")},
                            ],
                            "volumeMounts": [{"name": "runner-vol", "mountPath": "/runner"}],
                        }],
                        "restartPolicy": "Never",
                        "volumes": [{"name": "runner-vol", "configMap": {"name": SYNC_PLAYBOOK_CONFIGMAP}}],
                    },
                },
                "ttlSecondsAfterFinished": 180,
                "backoffLimit": 0,
            },
        }

    def _run_sync_job(self) -> bool:
        namespace = self._layout.app_namespace
        job = self._apis.batch.create_namespaced_job(namespace=namespace, body=self.sync_job_manifest())
        if self._wait_for_job(job.metadata.name):
            log.info("User sync Job completed successfully.")
            return True
        log.error("User sync Job failed: review the Job logs for details.")
        return False

    def _wait_for_job(self, job_name: str) -> bool:
        """True when the Job completes, False if it fails, times out or cannot be read."""
        log.info(f"Polling for Job '{job_name}' status "
                 f"(Interval: {self._poll_interval}s, Timeout: {self._job_timeout}s)...")
        deadline = time.monotonic() + self._job_timeout
        while time.monotonic() < deadline:
            time.sleep(self._poll_interval)
            try:
                job = self._apis.batch.read_namespaced_job_status(name=job_name, namespace=self._layout.app_namespace)
            except ApiException as e:
                log.error(f"Error reading Job status: {e}")
                return False
            for condition in job.status.conditions or []:
                if condition.status != "True":
                    continue
                if condition.type == "Complete":
                    return True
                if condition.type == "Failed":
                    log.error(f"Job {job_name} failed. Reason: {condition.reason}, Message: {condition.message}")
                    return False
        log.error(f"Job {job_name} timed out after {self._job_timeout} seconds.")
        return False
