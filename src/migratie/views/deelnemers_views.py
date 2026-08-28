"""
Module die de views bevat voor alle deelnemer gerelateerde zaken.
De views in deze module worden gebruikt voor het pad `/deelnemers/*`

## Functies:
    **deelnemers_lijst:** Geeft een view voor het oplijsten van alle deelnemers
    **deelnemers_detail:** Geeft een view voor het tonen van details over een deelnemer
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from migratie.models import Inschrijving, Lid

from migratie.utils.soap import haal_lidgegevens


@login_required
def deelnemers_lijst(request: HttpRequest) -> HttpResponse:
    """View voor het oplijsten van alle deelnemers in de databank.
    Deze view wordt gebruikt voor `/deelnemers/`.

    Args:
        request (HttpRequest): HTTP request voor de pagina

    Returns:
        HttpResponse: HTML document dat de pagina voorstelt
    """
    zoekterm = request.GET.get("q", '')
    deelnemers = Lid.objects.filter(
        Q(id__icontains=zoekterm)
        | Q(voornaam__icontains=zoekterm)
        | Q(achternaam__icontains=zoekterm)
        | Q(mailadres__icontains=zoekterm)
    ).distinct()

    return render(request, "deelnemers/deelnemers_lijst.html", {
        "deelnemers": deelnemers
    })


@login_required
def deelnemers_detail(request: HttpRequest, id: str) -> HttpResponse:
    """View voor het weergeven van de details van een deelnemer.
    Deze view wordt gebruikt voor `/deelnemers/<str:id>/`

    Args:
        request (HttpRequest): HTTP request voor de pagina
        id (str): id van de deelnemer, wordt bepaald door de URL

    Returns:
        HttpResponse: HTML document dat de pagina voorstelt
    """
    deelnemer = haal_lidgegevens(id)

    return render(request, "deelnemers/deelnemers_detail.html", {
        "deelnemer": deelnemer
    })