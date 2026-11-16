"""Settings from environment variables and the namespace layout derived from them."""
import pytest

from settings import LOCAL_KEYCLOAK_ISSUER, NamespaceLayout, Settings

ENV_VARS = [
    "KEYCLOAK_ISSUER", "KEYCLOAK_CERTS_URL", "CORS_ALLOWED_ORIGINS", "CLUSTER_CONNECTOR", "AGENT_MANAGER",
    "APP_NAMESPACE", "USER_NAMESPACE_PREFIX", "IMAGE_REGISTRY", "IMAGE_NAMESPACE", "HOSTNAME",
]


@pytest.fixture
def env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def detected(namespace="obs-demo"):
    calls = []

    def detect():
        calls.append(1)
        return namespace

    detect.calls = calls
    return detect


def test_defaults_reproduce_the_historical_behaviour(env):
    settings = Settings()
    assert settings.issuer == LOCAL_KEYCLOAK_ISSUER
    assert settings.certs_url == f"{LOCAL_KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
    assert settings.cors_origins == []
    assert not settings.uses_mock_cluster and not settings.uses_mock_agents

    layout = NamespaceLayout(settings, detected("obs-demo"))
    assert layout.app_namespace == "obs-demo"
    assert layout.user_namespace("abc") == "obs-demo-abc"
    assert layout.image("obs-sync-users") == "image-registry.openshift-image-registry.svc:5000/obs-demo/obs-sync-users"


def test_namespace_layout_from_environment(env):
    env.setenv("APP_NAMESPACE", "obs-lab")
    env.setenv("USER_NAMESPACE_PREFIX", "obs-usr-")
    env.setenv("IMAGE_REGISTRY", "quay.io")
    env.setenv("IMAGE_NAMESPACE", "csa-rh")
    detect = detected("ignored")
    layout = NamespaceLayout(Settings(), detect)
    assert layout.app_namespace == "obs-lab"
    assert layout.user_namespace("abc") == "obs-usr-abc"
    assert layout.image("obs-client-node:latest") == "quay.io/csa-rh/obs-client-node:latest"
    assert detect.calls == []


def test_prefix_and_images_follow_app_namespace_when_unset(env):
    env.setenv("APP_NAMESPACE", "obs-lab")
    layout = NamespaceLayout(Settings(), detected())
    assert layout.user_namespace_prefix == "obs-lab-"
    assert layout.image("x") == "image-registry.openshift-image-registry.svc:5000/obs-lab/x"


def test_empty_prefix_is_allowed(env):
    env.setenv("USER_NAMESPACE_PREFIX", "")
    assert NamespaceLayout(Settings(), detected()).user_namespace("abc") == "abc"


def test_namespace_detected_once(env):
    detect = detected()
    layout = NamespaceLayout(Settings(), detect)
    layout.user_namespace("a")
    layout.user_namespace("b")
    layout.image("x")
    assert len(detect.calls) == 1


@pytest.mark.parametrize(
    "issuer, local",
    [(None, False), ("https://keycloak.apps.example.com/realms/csa", False),
     ("https://localhost:8443/realms/csa", True), ("https://127.0.0.1:8443/realms/csa", True)],
)
def test_local_keycloak_detection(env, issuer, local):
    """Unset issuer is NOT local mode: the sync Job must not be skipped by accident."""
    if issuer:
        env.setenv("KEYCLOAK_ISSUER", issuer)
    assert Settings().is_local_keycloak is local


def test_explicit_certs_url_and_backends(env):
    env.setenv("KEYCLOAK_CERTS_URL", "https://idp/certs")
    env.setenv("CLUSTER_CONNECTOR", "mock")
    env.setenv("AGENT_MANAGER", "mock")
    settings = Settings()
    assert settings.certs_url == "https://idp/certs"
    assert settings.uses_mock_cluster and settings.uses_mock_agents
