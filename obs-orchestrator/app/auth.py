"""Keycloak JWT validation for the API.

Tokens are RS256 JWTs issued by the Keycloak realm. Their signing keys come from the realm JWKS
endpoint and are cached in memory (see `JWKSCache`), so Keycloak is not called on every request.
"""
import logging
import threading
import time
from typing import Callable, Dict, Optional

import requests                                                     # type: ignore
from fastapi import Depends, HTTPException                          # type: ignore
from fastapi.security import HTTPBearer                             # type: ignore
import jwt                                                          # type: ignore  (PyJWT)

from settings import settings

log = logging.getLogger(__name__)

KEYCLOAK_ISSUER = settings.issuer
KEYCLOAK_AUDIENCE = settings.keycloak_audience
KEYCLOAK_CERTS_URL = settings.certs_url
ALGORITHM = "RS256"
log.info(f"IdP issuer: {KEYCLOAK_ISSUER}")


class JWKSCache:
    """In-memory cache of the realm signing keys, indexed by `kid`.

    - Keys are reused for `ttl` seconds, then re-fetched.
    - An unknown `kid` (Keycloak rotated its keys) forces a re-fetch, but at most once every
      `min_refresh_interval` seconds, so tokens with bogus `kid`s cannot hammer Keycloak.
    - If a re-fetch fails, keys fetched earlier keep being used.
    """

    def __init__(self, url: str, ttl: float = 300, min_refresh_interval: float = 10,
                 fetch_timeout: float = 5, clock: Callable[[], float] = time.monotonic):
        self.url = url
        self.ttl = ttl
        self.min_refresh_interval = min_refresh_interval
        self.fetch_timeout = fetch_timeout
        self._clock = clock
        self._lock = threading.Lock()
        self.clear()

    def clear(self):
        self._keys: Dict[str, dict] = {}
        self._fetched_at: Optional[float] = None

    def _age(self) -> float:
        return float("inf") if self._fetched_at is None else self._clock() - self._fetched_at

    def _refresh(self):
        # Mark the attempt first: a failing Keycloak is also retried at most once per interval.
        self._fetched_at = self._clock()
        response = requests.get(self.url, timeout=self.fetch_timeout)
        response.raise_for_status()
        # Keycloak also publishes encryption keys ("use": "enc"); only signing keys verify tokens.
        self._keys = {
            key["kid"]: key for key in response.json()["keys"]
            if "kid" in key and key.get("use", "sig") == "sig"
        }

    def get_key(self, kid: str) -> dict:
        """Return the JWK for `kid`. 401 if Keycloak does not know it, 500 if unreachable."""
        with self._lock:
            age = self._age()
            expired = age >= self.ttl
            unknown_kid = kid not in self._keys and age >= self.min_refresh_interval
            if expired or unknown_kid:
                try:
                    self._refresh()
                except requests.RequestException as e:
                    if kid not in self._keys:
                        raise HTTPException(status_code=500, detail=f"Error fetching public keys: {e}")
                    log.warning(f"JWKS refresh failed, using cached keys: {e}")
            key = self._keys.get(kid)
        if key is None:
            raise HTTPException(status_code=401, detail="Public key not found")
        return key


jwks_cache = JWKSCache(KEYCLOAK_CERTS_URL)


def decode_token(token: str) -> Dict:
    """Validate signature, expiry, audience and issuer; return the claims."""
    try:
        kid = jwt.get_unverified_header(token).get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token header missing 'kid'")
        # The key is built for RS256 explicitly, never from the token header (algorithm confusion).
        key = jwt.PyJWK(jwks_cache.get_key(kid), algorithm=ALGORITHM).key
        return jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
            options={"require": ["exp", "iss", "aud"]},
        )
    except HTTPException:
        raise
    except (jwt.PyJWTError, jwt.PyJWKError) as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error decoding token: {e}")


security = HTTPBearer()


def get_current_user(authorization=Depends(security)) -> str:
    """FastAPI dependency: the `preferred_username` of the caller. Any failure is a 401."""
    try:
        return decode_token(authorization.credentials)["preferred_username"]
    except HTTPException as e:
        log.warning(f"rejected token ({e.status_code}): {e.detail}")
        raise HTTPException(status_code=401, detail=f"Unauthorized: {e.detail}")
    except Exception as e:
        log.warning(f"rejected token: {e}")
        raise HTTPException(status_code=401, detail=f"Unauthorized: {e}")
