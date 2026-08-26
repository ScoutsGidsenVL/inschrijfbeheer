"""
Aangepaste OpenID Connect-authenticatiebackend voor Keycloak.

Cachet de JWKS-sleutels van Keycloak in plaats van ze bij elke login
opnieuw op te vragen. Dat voorkomt dat de aanmeldserver van SGV je
project rate-limit tijdens testen, en verlaagt de belasting op die
gedeelde infrastructuur in productie. Keycloak wisselt zijn signing
keys zelden, dus een uur cachen is veilig.
"""

import requests
import jwt
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

JWKS_CACHE_KEY = "keycloak_jwks"
JWKS_CACHE_TIMEOUT = 3600  # 1 uur


class KeycloakOIDCBackend(OIDCAuthenticationBackend):
    def retrieve_matching_jwk(self, token):
        jwks = cache.get(JWKS_CACHE_KEY)

        if jwks is None:
            response = requests.get(
                self.OIDC_OP_JWKS_ENDPOINT,
                verify=self.get_settings("OIDC_VERIFY_SSL", True),
                timeout=self.get_settings("OIDC_TIMEOUT", None),
                proxies=self.get_settings("OIDC_PROXY", None),
            )
            response.raise_for_status()
            jwks = response.json()
            cache.set(JWKS_CACHE_KEY, jwks, JWKS_CACHE_TIMEOUT)

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

        return key