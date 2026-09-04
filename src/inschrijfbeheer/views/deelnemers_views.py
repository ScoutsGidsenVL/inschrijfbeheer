"""
Module die de views bevat voor alle deelnemer gerelateerde zaken.
De views in deze module worden gebruikt voor het pad `/deelnemers/*`

## Functies:
    **deelnemers_lijst:** Geeft een view voor het oplijsten van alle deelnemers
    **deelnemers_detail:** Geeft een view voor het tonen van details over een deelnemer
    **deelnemers_inschrijvingen:** Geeft een view voor het tonen van de inschrijvingen van een deelnemer
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from inschrijfbeheer.models import Inschrijving, Deelnemer

from inschrijfbeheer.utils.soap import haal_lidgegevens
from inschrijfbeheer.utils.auth import check_rollen


@login_required
@check_rollen
def deelnemers_lijst(request: HttpRequest) -> HttpResponse:
    """View voor het oplijsten van alle deelnemers in de databank.
    Deze view wordt gebruikt voor `/deelnemers/`.

    De pagina laat filtering toe op basis van het id, de naam of het mailadres van de deelnemer.

    Args:
        request (HttpRequest): HTTP request voor de pagina

    Returns:
        HttpResponse: HTML document dat de pagina voorstelt
    """
    zoekterm = request.GET.get("q", '')
    deelnemers = Deelnemer.objects.filter(
        Q(id__icontains=zoekterm)
        | Q(voornaam__icontains=zoekterm)
        | Q(achternaam__icontains=zoekterm)
        | Q(mailadres__icontains=zoekterm)
    ).distinct()

    return render(request, "deelnemers/deelnemers_lijst.html", {
        "deelnemers": deelnemers
    })


@login_required
@check_rollen
def deelnemers_detail(request: HttpRequest, id: str) -> HttpResponse:
    """View voor het weergeven van de details van een deelnemer.
    Deze view wordt gebruikt voor `/deelnemers/<str:id>/`

    Args:
        request (HttpRequest): HTTP request voor de pagina
        id (str): id van de deelnemer, wordt bepaald door de URL

    Returns:
        HttpResponse: HTML document dat de pagina voorstelt
    """
    deelnemer = Deelnemer.objects.get(id=id)
    if deelnemer.foutboodschap is not None:
        return render(request, "deelnemers/deelnemers_ongeldig.html", {
            "deelnemer": deelnemer,
        })
    
    gegevens = haal_lidgegevens(id)
    return render(request, "deelnemers/deelnemers_detail.html", {
        "deelnemer": deelnemer,
        "gegevens": gegevens,
    })

@login_required
@check_rollen
def deelnemers_inschrijvingen(request: HttpRequest, id: str) -> HttpResponse:
    """View die alle inschrijvingen voor een deelnemer oplijst.
    Deze view wordt gebruikt voor /deelnemers/<id>/inschrijvingen.

    De pagina laat filtering toe op basis van de naam of het id van een evenement en de aanwezigheid van de deelnemer.

    Args:
        request (HttpRequest): HTTP request voor de pagina
        id (str): id van de deelnemer, wordt bepaald door de URL

    Returns:
        HttpResponse: HTML document dat de pagina voorstelt
    """
    deelnemer = Deelnemer.objects.get(id=id)
    zoekterm = request.GET.get('q', '')
    aanwezig_filter = request.GET.get("aanwezig", '')

    inschrijvingen = Inschrijving.objects.filter(lid=id).select_related("evenement")

    if zoekterm:
        inschrijvingen = inschrijvingen.filter(
            Q(evenement__id__icontains=zoekterm)
            | Q(evenement__titel__icontains=zoekterm)
        )

    if aanwezig_filter == '1':
        inschrijvingen = inschrijvingen.filter(annulatie__isnull=True)
    elif aanwezig_filter == '0':
        inschrijvingen = inschrijvingen.exclude(annulatie__isnull=True)

    return render(request, "deelnemers/deelnemers_inschrijvingen.html", {
        "inschrijvingen": inschrijvingen,
        "deelnemer": deelnemer,
    })