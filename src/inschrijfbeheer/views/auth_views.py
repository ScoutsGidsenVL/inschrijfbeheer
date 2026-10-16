"""Views rond aanmelden en afmelden"""

import logging

from django.conf import settings
from django.contrib import auth
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_exempt

logger = logging.getLogger("inschrijfbeheer")


@never_cache
@xframe_options_exempt
def frontchannel_logout(request: HttpRequest) -> HttpResponse:
    """Front-channel logout van Keycloak, voor `/oidc/frontchannel-logout/`

    Bij het afmelden laadt Keycloak deze URL in een iframe, met `iss` en `sid`
    als parameters. Komen ze overeen met de sessie, dan wordt de gebruiker ook
    hier afgemeld. Het antwoord is altijd leeg.

    Args:
        request (HttpRequest): HTTP request van de iframe van Keycloak

    Returns:
        HttpResponse: een lege response
    """
    iss = request.GET.get("iss")
    sid = request.GET.get("sid")

    if (
        request.user.is_authenticated
        and iss == settings.KEYCLOAK_REALM_URL
        and sid
        and sid == request.session.get("oidc_sid")
    ):
        logger.info("Gebruiker %s afgemeld via Keycloak", request.user)
        auth.logout(request)

    return HttpResponse(status=200)


def geen_toegang(request: HttpRequest) -> HttpResponse:
    """Pagina voor wie niet aangemeld is of geen toegang heeft, voor `/geen-toegang/`

    Args:
        request (HttpRequest): HTTP request voor de pagina

    Returns:
        HttpResponse: de pagina met een knop om aan te melden
    """
    return render(request, "geen_toegang.html")
