"""CORS origins come from CORS_ALLOWED_ORIGINS (the obs-console URL)."""
import pytest
from fastapi.testclient import TestClient

import main
from settings import Settings


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, ["*"]),
        ("", ["*"]),
        ("https://obs-console.apps.example.com", ["https://obs-console.apps.example.com"]),
        (" https://a.example.com/ , https://b.example.com ", ["https://a.example.com", "https://b.example.com"]),
    ],
)
def test_cors_allowed_origins(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", value)
    assert main.get_cors_allowed_origins(Settings()) == expected


def _preflight(origin):
    with TestClient(main.app) as client:
        return client.options(
            "/api/v1/users",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET",
                     "Access-Control-Request-Headers": "authorization"},
        )


def test_preflight_from_console_is_allowed():
    # Tests run without CORS_ALLOWED_ORIGINS: any origin, no credentials.
    response = _preflight("https://obs-console.apps.example.com")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
