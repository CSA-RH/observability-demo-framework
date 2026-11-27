"""JWT validation against Keycloak, using a throwaway RSA key instead of a real IdP."""
import time

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
import jwt
from jwt.algorithms import RSAAlgorithm

import auth

KID = "test-key"


def _rsa_pem():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


PRIVATE_PEM = _rsa_pem()
OTHER_PRIVATE_PEM = _rsa_pem()
PUBLIC_KEY = serialization.load_pem_private_key(PRIVATE_PEM, password=None).public_key()
PUBLIC_JWK = {**RSAAlgorithm.to_jwk(PUBLIC_KEY, as_dict=True), "kid": KID, "use": "sig", "alg": "RS256"}


def make_token(private_pem=PRIVATE_PEM, kid=KID, algorithm="RS256", **claim_overrides):
    claims = {
        "preferred_username": "alice",
        "iss": auth.KEYCLOAK_ISSUER,
        "aud": auth.KEYCLOAK_AUDIENCE,
        "exp": int(time.time()) + 300,
    }
    claims.update(claim_overrides)
    claims = {k: v for k, v in claims.items() if v is not None}  # None removes a claim
    headers = {"kid": kid} if kid else {}
    return jwt.encode(claims, private_pem, algorithm=algorithm, headers=headers)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def empty_jwks_cache():
    auth.jwks_cache.clear()
    yield
    auth.jwks_cache.clear()


@pytest.fixture
def jwks_requests(monkeypatch):
    """Serve the test JWKS instead of calling Keycloak; records each fetch."""
    calls = []

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        return FakeResponse({"keys": [PUBLIC_JWK]})

    monkeypatch.setattr(auth.requests, "get", fake_get)
    return calls


def get_info(client, token):
    return client.get("/api/v1/escotilla", headers={"Authorization": f"Bearer {token}"})


def test_missing_token_is_rejected(anonymous_client):
    assert anonymous_client.get("/api/v1/escotilla").status_code in (401, 403)


def test_valid_token_resolves_preferred_username(anonymous_client, jwks_requests):
    response = get_info(anonymous_client, make_token())
    assert response.status_code == 200
    assert response.json()["Namespace"] == "fake-namespace-alice"
    assert jwks_requests == [auth.KEYCLOAK_CERTS_URL]


@pytest.mark.parametrize(
    "token_kwargs",
    [
        pytest.param({"exp": int(time.time()) - 10}, id="expired"),
        pytest.param({"aud": "someone-else"}, id="wrong-audience"),
        pytest.param({"iss": "https://evil.example/realms/csa"}, id="wrong-issuer"),
        pytest.param({"kid": None}, id="missing-kid"),
        pytest.param({"kid": "unknown-kid"}, id="unknown-kid"),
        pytest.param({"private_pem": OTHER_PRIVATE_PEM}, id="bad-signature"),
    ],
)
def test_invalid_tokens_are_rejected(anonymous_client, jwks_requests, token_kwargs):
    response = get_info(anonymous_client, make_token(**token_kwargs))
    assert response.status_code == 401


def test_garbage_token_is_rejected(anonymous_client, jwks_requests):
    assert get_info(anonymous_client, "not-a-jwt").status_code == 401


def test_keycloak_unreachable_results_in_401(anonymous_client, monkeypatch):
    def unreachable(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(auth.requests, "get", unreachable)
    assert get_info(anonymous_client, make_token()).status_code == 401


def test_jwks_cache_errors(monkeypatch):
    monkeypatch.setattr(auth.requests, "get", lambda *a, **k: FakeResponse({"keys": [PUBLIC_JWK]}))
    with pytest.raises(HTTPException) as exc:
        auth.jwks_cache.get_key("unknown-kid")
    assert exc.value.status_code == 401

    auth.jwks_cache.clear()

    def unreachable(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(auth.requests, "get", unreachable)
    with pytest.raises(HTTPException) as exc:
        auth.jwks_cache.get_key(KID)
    assert exc.value.status_code == 500


def test_jwks_is_cached_between_requests(anonymous_client, jwks_requests):
    token = make_token()
    assert get_info(anonymous_client, token).status_code == 200
    assert get_info(anonymous_client, token).status_code == 200
    assert len(jwks_requests) == 1


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock_cache(jwks_requests):
    clock = FakeClock()
    return auth.JWKSCache("https://idp/certs", ttl=300, min_refresh_interval=10, clock=clock), clock


def test_jwks_refetched_after_ttl(clock_cache, jwks_requests):
    cache, clock = clock_cache
    cache.get_key(KID)
    clock.now += 299
    cache.get_key(KID)
    assert len(jwks_requests) == 1
    clock.now += 1
    cache.get_key(KID)
    assert len(jwks_requests) == 2


def test_unknown_kid_refetch_is_rate_limited(clock_cache, jwks_requests):
    cache, clock = clock_cache
    cache.get_key(KID)
    for _ in range(5):
        with pytest.raises(HTTPException):
            cache.get_key("rotated-kid")
    assert len(jwks_requests) == 1
    clock.now += 10
    with pytest.raises(HTTPException):
        cache.get_key("rotated-kid")
    assert len(jwks_requests) == 2


def test_unknown_kid_found_after_key_rotation(clock_cache, monkeypatch):
    cache, clock = clock_cache
    cache.get_key(KID)
    rotated = {**PUBLIC_JWK, "kid": "rotated-kid"}
    monkeypatch.setattr(auth.requests, "get", lambda *a, **k: FakeResponse({"keys": [PUBLIC_JWK, rotated]}))
    clock.now += 10
    assert cache.get_key("rotated-kid")["kid"] == "rotated-kid"


def test_cached_keys_survive_keycloak_outage(clock_cache, monkeypatch):
    cache, clock = clock_cache
    cache.get_key(KID)

    def unreachable(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(auth.requests, "get", unreachable)
    clock.now += 301
    assert cache.get_key(KID)["kid"] == KID


def test_jwks_fetch_has_timeout(monkeypatch):
    seen = {}

    def fake_get(url, *args, **kwargs):
        seen.update(kwargs)
        return FakeResponse({"keys": [PUBLIC_JWK]})

    monkeypatch.setattr(auth.requests, "get", fake_get)
    auth.jwks_cache.get_key(KID)
    assert seen.get("timeout")


def _public_pem():
    return PUBLIC_KEY.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def _unsigned_token(claims, kid=KID):
    """alg=none token, built by hand (PyJWT refuses to verify these, which is what we test)."""
    import base64
    import json

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    return f"{b64({'alg': 'none', 'typ': 'JWT', 'kid': kid})}.{b64(claims)}."


def _valid_claims():
    return {"preferred_username": "mallory", "iss": auth.KEYCLOAK_ISSUER, "aud": auth.KEYCLOAK_AUDIENCE,
            "exp": int(time.time()) + 300}


def test_algorithm_confusion_hs256_with_public_key_is_rejected(anonymous_client, jwks_requests):
    """CVE-2026-85394 class: HS256 token whose HMAC secret is the realm's public key."""
    import hashlib
    import hmac
    import base64
    import json

    def b64(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    payload = b64(json.dumps(_valid_claims()).encode())
    signature = b64(hmac.new(_public_pem(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    assert get_info(anonymous_client, f"{header}.{payload}.{signature}").status_code == 401


def test_unsigned_token_is_rejected(anonymous_client, jwks_requests):
    assert get_info(anonymous_client, _unsigned_token(_valid_claims())).status_code == 401


@pytest.mark.parametrize("claim", ["exp", "iss", "aud"])
def test_tokens_without_required_claims_are_rejected(anonymous_client, jwks_requests, claim):
    assert get_info(anonymous_client, make_token(**{claim: None})).status_code == 401


def test_encryption_keys_are_not_used_for_signatures(anonymous_client, monkeypatch):
    enc_key = {**PUBLIC_JWK, "use": "enc"}
    monkeypatch.setattr(auth.requests, "get", lambda *a, **k: FakeResponse({"keys": [enc_key]}))
    assert get_info(anonymous_client, make_token()).status_code == 401


def list_users(client, token):
    return client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})


def test_admin_role_comes_from_realm_access(anonymous_client, jwks_requests):
    admin = make_token(preferred_username="boss", realm_access={"roles": ["default-roles-csa", auth.ADMIN_ROLE]})
    assert list_users(anonymous_client, admin).status_code == 200


@pytest.mark.parametrize("claims", [
    pytest.param({}, id="no-realm-access"),
    pytest.param({"realm_access": {"roles": ["default-roles-csa"]}}, id="other-roles"),
    pytest.param({"preferred_username": "admin"}, id="admin-username-without-role"),
    pytest.param({"resource_access": {"obs-console": {"roles": [auth.ADMIN_ROLE]}}}, id="client-role-is-not-enough"),
])
def test_tokens_without_the_admin_realm_role_are_forbidden(anonymous_client, jwks_requests, claims):
    assert list_users(anonymous_client, make_token(**claims)).status_code == 403
