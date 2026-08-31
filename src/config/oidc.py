import time
import requests
import jwt
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

JWKS_CACHE_KEY = "keycloak_jwks"
JWKS_STALE_CACHE_KEY = "keycloak_jwks_stale"
JWKS_CACHE_TIMEOUT = 3600  # 1 uur, verse waarde
JWKS_STALE_TIMEOUT = 7 * 24 * 3600  # 1 week, valt terug bij storing
JWKS_LOCK_KEY = "keycloak_jwks_lock"
JWKS_FAILURE_BACKOFF = 30  # seconden, geen nieuwe poging binnen dit venster


class KeycloakOIDCBackend(OIDCAuthenticationBackend):
    def retrieve_matching_jwk(self, token):
        jwks = cache.get(JWKS_CACHE_KEY)

        if jwks is None:
            jwks = self._fetch_jwks_met_terugval()

        header = jwt.get_unverified_header(token)
        key = None
        for jwk in jwks["keys"]:
            if jwk["kid"] != header["kid"]:
                continue
            if "alg" in jwk and jwk["alg"] != header["alg"]:
                raise SuspiciousOperation("alg values do not match.")
            key = jwk

        if key is None:
            raise SuspiciousOperation("Could not find a valid JWKS.")

        return jwt.PyJWK(key)

    def _fetch_jwks_met_terugval(self):
        # Voorkomt dat meerdere workers gelijktijdig ophalen bij een cache-miss.
        if not cache.add(JWKS_LOCK_KEY, "1", timeout=JWKS_FAILURE_BACKOFF):
            stale = cache.get(JWKS_STALE_CACHE_KEY)
            if stale is not None:
                return stale
            time.sleep(1)
            jwks = cache.get(JWKS_CACHE_KEY)
            if jwks is not None:
                return jwks

        try:
            response = requests.get(
                self.OIDC_OP_JWKS_ENDPOINT,
                headers={"User-Agent": "inschrijfbeheer-oidc/1.0"},
                verify=self.get_settings("OIDC_VERIFY_SSL", True),
                timeout=self.get_settings("OIDC_TIMEOUT", 5),
                proxies=self.get_settings("OIDC_PROXY", None),
            )
            response.raise_for_status()
            jwks = response.json()
        except requests.RequestException:
            stale = cache.get(JWKS_STALE_CACHE_KEY)
            if stale is not None:
                return stale
            raise

        cache.set(JWKS_CACHE_KEY, jwks, JWKS_CACHE_TIMEOUT)
        cache.set(JWKS_STALE_CACHE_KEY, jwks, JWKS_STALE_TIMEOUT)
        return jwks