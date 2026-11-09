"""JWT validation against Keycloak, using a throwaway RSA key instead of a real IdP."""
import time

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwk, jwt

import main

KID = "test-key"


def _rsa_pem():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


PRIVATE_PEM = _rsa_pem()
OTHER_PRIVATE_PEM = _rsa_pem()
PUBLIC_JWK = {**jwk.construct(PRIVATE_PEM, "RS256").public_key().to_dict(), "kid": KID}


def make_token(private_pem=PRIVATE_PEM, kid=KID, **claim_overrides):
    claims = {
        "preferred_username": "alice",
        "iss": main.KEYCLOAK_ISSUER,
        "aud": main.KEYCLOAK_AUDIENCE,
        "exp": int(time.time()) + 300,
    }
    claims.update(claim_overrides)
    headers = {"kid": kid} if kid else {}
    return jwt.encode(claims, private_pem, algorithm="RS256", headers=headers)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def jwks_requests(monkeypatch):
    """Serve the test JWKS instead of calling Keycloak; records each fetch."""
    calls = []

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        return FakeResponse({"keys": [PUBLIC_JWK]})

    monkeypatch.setattr(main.requests, "get", fake_get)
    return calls


def get_info(client, token):
    return client.get("/api/v1/escotilla", headers={"Authorization": f"Bearer {token}"})


def test_missing_token_is_rejected(anonymous_client):
    assert anonymous_client.get("/api/v1/escotilla").status_code in (401, 403)


def test_valid_token_resolves_preferred_username(anonymous_client, jwks_requests):
    response = get_info(anonymous_client, make_token())
    assert response.status_code == 200
    assert response.json()["Namespace"] == "fake-namespace-alice"
    assert jwks_requests == [main.KEYCLOAK_CERTS_URL]


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

    monkeypatch.setattr(main.requests, "get", unreachable)
    assert get_info(anonymous_client, make_token()).status_code == 401


def test_get_public_key_errors(monkeypatch):
    monkeypatch.setattr(main.requests, "get", lambda *a, **k: FakeResponse({"keys": [PUBLIC_JWK]}))
    with pytest.raises(HTTPException) as exc:
        main.get_public_key("unknown-kid")
    assert exc.value.status_code == 401

    def unreachable(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(main.requests, "get", unreachable)
    with pytest.raises(HTTPException) as exc:
        main.get_public_key(KID)
    assert exc.value.status_code == 500


@pytest.mark.xfail(strict=True, reason="Known gap: JWKS is fetched from Keycloak on every request (should be cached)")
def test_jwks_is_cached_between_requests(anonymous_client, jwks_requests):
    token = make_token()
    get_info(anonymous_client, token)
    get_info(anonymous_client, token)
    assert len(jwks_requests) == 1
