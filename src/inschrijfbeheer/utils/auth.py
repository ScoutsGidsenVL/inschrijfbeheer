"""Module met extra functies/decorators voor de authenticatie/autorisatie van Inschrijfbeheer
"""
from dotenv import load_dotenv
import os
from functools import wraps
from django.contrib.auth.decorators import login_required

import requests
from django.http import Http404

load_dotenv()
GA_API = os.getenv("GA_RESTAPI_URL")

def haal_groepen(request):
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
        GA_API + "groep",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()

    return response.json()


def check_rollen(func):
    """Functie die een decorator teruggeeft voor een bepaalde rol die gecheckt moet worden

    Args:
        rol (str, optional): de rol die de persoon moet hebben binnen X1207G. Defaults to "personeel".
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            profiel = haal_groepen(request)
            for groep in profiel.get("groepen", []):
                if groep.get("id") == "X1027G":
                    for verantwoordelijkheid in groep.get("verantwoordelijkheden", []):
                        if verantwoordelijkheid == "personeel":
                            return func(request, *args, **kwargs)
        except (requests.RequestException, ValueError, AttributeError):
            raise Http404()

        raise Http404()

    return login_required(wrapper)
