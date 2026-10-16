"""Module met extra functies/decorators voor de authenticatie/autorisatie van Inschrijfbeheer"""

import logging
import os
import time
from functools import wraps

import requests
from django.contrib.auth.decorators import login_required
from django.http import Http404
from dotenv import load_dotenv

load_dotenv()
GA_API = os.getenv("GA_RESTAPI_URL")

# Groep en verantwoordelijkheid in Groepsadmin die toegang geven tot Inschrijfbeheer
PERSONEEL_GROEP = "X1027G"
PERSONEEL_VERANTWOORDELIJKHEID = "personeel"

# Hoe lang een geslaagde controle bij Groepsadmin geldig blijft in de sessie
TOEGANG_CACHE_SECONDEN = 300
TOEGANG_SESSIE_SLEUTEL = "personeel_gecontroleerd_op"

logger = logging.getLogger("inschrijfbeheer")


def is_personeel(access_token: str | None) -> bool:
    """Controleert bij Groepsadmin of de gebruiker personeel is.

    Gebruikt het Keycloak access token van de gebruiker om zijn profiel op te
    vragen bij de Groepsadmin REST-API.

    Args:
        access_token: het Keycloak access token van de gebruiker.

    Returns:
        bool: True als de gebruiker in groep X1027G de verantwoordelijkheid
            "personeel" heeft.

    Raises:
        requests.RequestException: als de aanvraag naar Groepsadmin mislukt.
        ValueError: als Groepsadmin geen geldige JSON teruggeeft.
    """
    response = requests.get(
        GA_API + "groep",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()

    for groep in response.json().get("groepen", []):
        if groep.get("id") != PERSONEEL_GROEP:
            continue
        if PERSONEEL_VERANTWOORDELIJKHEID in groep.get("verantwoordelijkheden", []):
            return True

    return False


def onthoud_toegang(session) -> None:
    """Bewaart in de sessie dat de gebruiker net als personeel gecontroleerd is."""
    session[TOEGANG_SESSIE_SLEUTEL] = time.time()


def check_rollen(func):
    """Decorator die enkel personeel toelaat tot een view.

    Een geslaagde controle bij Groepsadmin blijft TOEGANG_CACHE_SECONDEN geldig in
    de sessie. Zo spreekt niet elke request Groepsadmin aan. Een negatief
    resultaat wordt niet bewaard.

    Args:
        func (function): view waarvoor gecontroleerd moet worden
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        gecontroleerd_op = request.session.get(TOEGANG_SESSIE_SLEUTEL, 0)
        if time.time() - gecontroleerd_op < TOEGANG_CACHE_SECONDEN:
            return func(request, *args, **kwargs)

        try:
            toegang = is_personeel(request.session.get("oidc_access_token"))
        except (requests.RequestException, ValueError, AttributeError):
            logger.exception(
                "check_rollen faalde voor gebruiker %s op %s %s",
                request.user,
                request.method,
                request.path,
            )
            raise Http404()

        if toegang:
            onthoud_toegang(request.session)
            return func(request, *args, **kwargs)

        logger.warning(
            "Gebruiker %s heeft geen toegang via %s/%s (%s %s)",
            request.user,
            PERSONEEL_GROEP,
            PERSONEEL_VERANTWOORDELIJKHEID,
            request.method,
            request.path,
        )
        raise Http404()

    return login_required(wrapper)
