import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from kubernetes import client  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore


USER_SYNC_LEASE_NAME = "user-sync-lock"
DEFAULT_LEASE_DURATION_SECONDS = 60
DEFAULT_ACQUIRE_TIMEOUT_SECONDS = 300
DEFAULT_RETRY_INTERVAL_SECONDS = 2


class LeaseLockError(RuntimeError):
    pass


class LeaseLock:
    """Kubernetes Lease-based mutex for serializing user sync jobs."""

    def __init__(
        self,
        coordination_api: client.CoordinationV1Api,
        namespace: str,
        lease_name: str = USER_SYNC_LEASE_NAME,
        holder_identity: str | None = None,
        lease_duration_seconds: int = DEFAULT_LEASE_DURATION_SECONDS,
        acquire_timeout_seconds: int = DEFAULT_ACQUIRE_TIMEOUT_SECONDS,
        retry_interval_seconds: int = DEFAULT_RETRY_INTERVAL_SECONDS,
    ):
        self._coordination_api = coordination_api
        self._namespace = namespace
        self._lease_name = lease_name
        self._holder_identity = holder_identity or os.getenv(
            "LEASE_HOLDER_IDENTITY",
            os.getenv("HOSTNAME", "obs-main-api"),
        )
        self._lease_duration_seconds = lease_duration_seconds
        self._acquire_timeout_seconds = acquire_timeout_seconds
        self._retry_interval_seconds = retry_interval_seconds
        self._acquired = False

    def acquire(self):
        deadline = time.time() + self._acquire_timeout_seconds
        while time.time() < deadline:
            if self._try_acquire_once():
                self._acquired = True
                return
            time.sleep(self._retry_interval_seconds)
        raise LeaseLockError(
            f"Timed out acquiring lease '{self._lease_name}' in namespace '{self._namespace}'"
        )

    def release(self):
        if not self._acquired:
            return
        try:
            self._coordination_api.delete_namespaced_lease(
                name=self._lease_name,
                namespace=self._namespace,
            )
        except ApiException as exc:
            if exc.status != 404:
                raise
        finally:
            self._acquired = False

    def _try_acquire_once(self) -> bool:
        now = datetime.now(timezone.utc)
        lease_body = client.V1Lease(
            metadata=client.V1ObjectMeta(
                name=self._lease_name,
                namespace=self._namespace,
                labels={"observability-demo-framework": "lease"},
            ),
            spec=client.V1LeaseSpec(
                holder_identity=self._holder_identity,
                lease_duration_seconds=self._lease_duration_seconds,
                acquire_time=now,
                renew_time=now,
            ),
        )

        try:
            existing = self._coordination_api.read_namespaced_lease(
                name=self._lease_name,
                namespace=self._namespace,
            )
        except ApiException as exc:
            if exc.status == 404:
                try:
                    self._coordination_api.create_namespaced_lease(
                        namespace=self._namespace,
                        body=lease_body,
                    )
                    return True
                except ApiException as create_exc:
                    if create_exc.status == 409:
                        return False
                    raise
            raise

        if self._is_lease_available(existing):
            existing.spec = lease_body.spec
            existing.metadata.labels = lease_body.metadata.labels
            self._coordination_api.replace_namespaced_lease(
                name=self._lease_name,
                namespace=self._namespace,
                body=existing,
            )
            return True

        if existing.spec and existing.spec.holder_identity == self._holder_identity:
            existing.spec.renew_time = now
            self._coordination_api.replace_namespaced_lease(
                name=self._lease_name,
                namespace=self._namespace,
                body=existing,
            )
            return True

        return False

    def _is_lease_available(self, lease: client.V1Lease) -> bool:
        spec = lease.spec
        if spec is None or not spec.renew_time:
            return True

        renew_epoch = spec.renew_time.timestamp() if hasattr(spec.renew_time, "timestamp") else spec.renew_time
        lease_duration = spec.lease_duration_seconds or self._lease_duration_seconds
        return time.time() >= renew_epoch + lease_duration


@contextmanager
def user_sync_lease(coordination_api: client.CoordinationV1Api, namespace: str):
    lock = LeaseLock(coordination_api, namespace)
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()
