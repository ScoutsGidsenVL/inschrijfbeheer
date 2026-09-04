"""Module met extra functies/decorators voor de authenticatie/autorisatie van Inschrijfbeheer
"""
from functools import wraps

import requests
from django.conf import settings
from django.http import Http404

GROEPSADMIN_PROFIEL_URL = (
    "https://groepsadmin.scoutsengidsenvlaanderen.be/groepsadmin/rest-ga/lid/profiel"
)


def haal_lidgegevens(request):
    """Haalt het profiel van de ingelogde gebruiker op bij Groepsadmin.

    Gebruikt het Keycloak access token uit de sessie (opgeslagen door
    mozilla-django-oidc wanneer OIDC_STORE_ACCESS_TOKEN = True staat in de
    settings) om het profiel op te vragen bij de Groepsadmin REST-API.

    Args:
        request: de huidige Django request van de ingelogde gebruiker.

    Returns:
        dict: het profiel-object dat Groepsadmin teruggeeft, met onder
            andere een lijst "functies" met objecten die "groep" en "code"
            bevatten.

    Raises:
        requests.RequestException: als de aanvraag naar Groepsadmin
            mislukt of geen geldig antwoord oplevert.
    """
    access_token = request.session.get("oidc_access_token")

    response = requests.get(
        GROEPSADMIN_PROFIEL_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def check_rollen(rol="personeel"):
    """Functie die een decorator teruggeeft voor een bepaalde rol die gecheckt moet worden

    Args:
        rol (str, optional): de rol die de persoon moet hebben binnen X1207G. Defaults to "personeel".
    """
    def check_rollen_decorator(func):

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                profiel = haal_lidgegevens(request)
                for functie in profiel.get("functies", []):
                    if functie.get("groep") == "X1027G" and functie.get("code") == rol:
                        return func(request, *args, **kwargs)
            except (requests.RequestException, ValueError, AttributeError):
                raise Http404()

            raise Http404()

        return wrapper

    return check_rollen_decorator