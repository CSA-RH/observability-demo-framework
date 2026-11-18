"""Runtime configuration of the orchestrator, read once from environment variables.

Every setting is optional; the defaults reproduce the historical behaviour (everything derived
from the orchestrator's own namespace, in-cluster registry). Names are case-insensitive env vars,
e.g. `USER_NAMESPACE_PREFIX=obs-usr-`.
"""
from functools import cached_property
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

LOCAL_KEYCLOAK_ISSUER = "https://localhost:8443/realms/csa"


INTERNAL_REGISTRY = "image-registry.openshift-image-registry.svc:5000"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # --- Identity provider
    keycloak_issuer: Optional[str] = None
    """Realm issuer URL. Unset: the local development Keycloak (`dev-start.sh`)."""
    keycloak_certs_url: Optional[str] = None
    """JWKS endpoint. Unset: derived from the issuer."""
    keycloak_audience: str = "account"

    # --- HTTP
    cors_allowed_origins: str = ""
    """Comma-separated browser origins allowed to call the API (the obs-console URL)."""

    # --- Backends
    cluster_connector: str = "openshift"
    """`mock` for the in-memory connector (local development, tests)."""
    agent_manager: str = "openshift"
    """`mock` for the in-memory agent manager."""

    # --- Namespace layout and images
    app_namespace: Optional[str] = None
    """Namespace of the lab core (orchestrator, users ConfigMap, sync Job, `idp-data`).
    Unset: the namespace the orchestrator runs in (service account, or kube context locally)."""
    user_namespace_prefix: Optional[str] = None
    """User namespaces are `<prefix><username>`. Unset: `<app_namespace>-`."""
    image_registry: str = INTERNAL_REGISTRY
    image_namespace: Optional[str] = None
    """Registry namespace/organisation of the agent and sync-users images. Unset: app_namespace."""

    # --- Logging
    log_level: str = "INFO"
    log_format: str = "json"
    """`json` (one object per line, for OpenShift Logging/Loki) or `text` (local development)."""

    # --- Pod identity (set by Kubernetes)
    hostname: str = ""

    @property
    def issuer(self) -> str:
        return self.keycloak_issuer or LOCAL_KEYCLOAK_ISSUER

    @property
    def certs_url(self) -> str:
        return self.keycloak_certs_url or f"{self.issuer}/protocol/openid-connect/certs"

    @property
    def is_local_keycloak(self) -> bool:
        """The API validates tokens of a local Keycloak that is not the cluster IdP."""
        issuer = self.keycloak_issuer or ""
        return "localhost" in issuer or "127.0.0.1" in issuer

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip().rstrip("/") for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def uses_mock_cluster(self) -> bool:
        return self.cluster_connector == "mock"

    @property
    def uses_mock_agents(self) -> bool:
        return self.agent_manager == "mock"


class NamespaceLayout:
    """Names derived from the settings. `detect_namespace` is only called if APP_NAMESPACE is unset."""

    def __init__(self, settings: Settings, detect_namespace):
        self._settings = settings
        self._detect_namespace = detect_namespace

    @cached_property
    def app_namespace(self) -> str:
        return self._settings.app_namespace or self._detect_namespace()

    @property
    def user_namespace_prefix(self) -> str:
        prefix = self._settings.user_namespace_prefix
        return prefix if prefix is not None else f"{self.app_namespace}-"

    def user_namespace(self, username: str) -> str:
        return f"{self.user_namespace_prefix}{username}"

    @property
    def image_namespace(self) -> str:
        return self._settings.image_namespace or self.app_namespace

    @property
    def uses_internal_registry(self) -> bool:
        """Images are built in-cluster into ImageStreams of `image_namespace`."""
        return self._settings.image_registry.rstrip("/") == INTERNAL_REGISTRY

    def image(self, name: str) -> str:
        """Fully-qualified image reference, e.g. `<registry>/<namespace>/obs-sync-users`."""
        return f"{self._settings.image_registry}/{self.image_namespace}/{name}"


settings = Settings()
