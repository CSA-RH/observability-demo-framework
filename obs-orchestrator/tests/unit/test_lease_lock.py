import time
from datetime import datetime, timedelta, timezone

import pytest
from kubernetes import client
from kubernetes.client.rest import ApiException

from operations.lease_lock import LeaseLock, LeaseLockError, user_sync_lease


class FakeCoordinationApi:
    """Minimal in-memory stand-in for CoordinationV1Api."""

    def __init__(self, lease=None, create_status=None, delete_status=None):
        self.lease = lease
        self.create_status = create_status
        self.delete_status = delete_status
        self.replaced = 0
        self.deleted = 0

    def read_namespaced_lease(self, name, namespace):
        if self.lease is None:
            raise ApiException(status=404)
        return self.lease

    def create_namespaced_lease(self, namespace, body):
        if self.create_status:
            raise ApiException(status=self.create_status)
        self.lease = body

    def replace_namespaced_lease(self, name, namespace, body):
        self.replaced += 1
        self.lease = body

    def delete_namespaced_lease(self, name, namespace):
        self.deleted += 1
        if self.delete_status:
            raise ApiException(status=self.delete_status)
        self.lease = None


def lease(holder, renewed_seconds_ago, duration=60):
    renew = datetime.now(timezone.utc) - timedelta(seconds=renewed_seconds_ago)
    return client.V1Lease(
        metadata=client.V1ObjectMeta(name="user-sync-lock"),
        spec=client.V1LeaseSpec(holder_identity=holder, lease_duration_seconds=duration, renew_time=renew),
    )


def make_lock(api, **kwargs):
    kwargs.setdefault("acquire_timeout_seconds", 0.2)
    kwargs.setdefault("retry_interval_seconds", 0.01)
    return LeaseLock(api, "obs-demo", holder_identity="me", **kwargs)


def test_creates_lease_when_absent():
    api = FakeCoordinationApi()
    make_lock(api).acquire()
    assert api.lease.spec.holder_identity == "me"


def test_takes_over_expired_lease():
    api = FakeCoordinationApi(lease=lease("other", renewed_seconds_ago=120))
    make_lock(api).acquire()
    assert api.lease.spec.holder_identity == "me"
    assert api.replaced == 1


def test_renews_own_lease():
    api = FakeCoordinationApi(lease=lease("me", renewed_seconds_ago=1))
    make_lock(api).acquire()
    assert api.replaced == 1


def test_times_out_when_held_by_someone_else():
    api = FakeCoordinationApi(lease=lease("other", renewed_seconds_ago=1))
    start = time.time()
    with pytest.raises(LeaseLockError):
        make_lock(api).acquire()
    assert time.time() - start < 2


def test_create_conflict_is_retried_not_raised():
    api = FakeCoordinationApi(create_status=409)
    with pytest.raises(LeaseLockError):
        make_lock(api).acquire()


def test_unexpected_api_error_propagates():
    api = FakeCoordinationApi(create_status=500)
    with pytest.raises(ApiException):
        make_lock(api).acquire()


def test_release_is_noop_when_not_acquired():
    api = FakeCoordinationApi()
    make_lock(api).release()
    assert api.deleted == 0


def test_release_ignores_missing_lease_but_raises_other_errors():
    api = FakeCoordinationApi(delete_status=404)
    lock = make_lock(api)
    lock.acquire()
    lock.release()

    api = FakeCoordinationApi(delete_status=500)
    lock = make_lock(api)
    lock.acquire()
    with pytest.raises(ApiException):
        lock.release()


def test_context_manager_releases_on_error(monkeypatch):
    api = FakeCoordinationApi()
    with pytest.raises(RuntimeError):
        with user_sync_lease(api, "obs-demo"):
            assert api.lease is not None
            raise RuntimeError("job failed")
    assert api.lease is None
