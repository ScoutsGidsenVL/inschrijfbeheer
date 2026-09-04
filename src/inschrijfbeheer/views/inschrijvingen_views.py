"""Module die de views bevat voor alle inschrijvingen gerelateerde zaken

## Functies:
    **inschrijvingen_detail:** Geeft een view voor het tonen van alle details van een inschrijving
"""
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404
from inschrijfbeheer.models import Inschrijving, InschrijvingVraagAntwoord
from inschrijfbeheer.utils.auth import check_rollen
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mail

@check_rollen
def inschrijvingen_detail(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    """View voor het tonen van de details van een inschrijving.
    Deze view wordt gebruikt voor `/inschrijvingen/<id>`

    Args:
        request (HttpRequest): HTTP request voor de pagina
        inschrijving_id (str): id van de inschrijving

    Returns:
        HttpResponse: HTML document dat de pagina voorstelt
    """
    inschrijving = Inschrijving.objects.select_related("lid", "evenement").get(id=inschrijving_id)

    vraag_antwoorden = InschrijvingVraagAntwoord.objects.filter(inschrijving=inschrijving_id).select_related("vraag", "vraag__type").order_by("vraag__volgorde")
    return render(request, "inschrijvingen/inschrijvingen_detail.html", {
        "vraag_antwoorden" : vraag_antwoorden,
        "inschrijving": inschrijving,
    })



@check_rollen
def inschrijvingen_vragen(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    inschrijving = Inschrijving.objects.select_related("lid", "evenement").get(id=inschrijving_id)
    vraag_antwoorden = InschrijvingVraagAntwoord.objects.filter(inschrijving=inschrijving_id).select_related("vraag", "vraag__type").order_by("vraag__volgorde")

    return render(request, "inschrijvingen/inschrijvingen_vragen.html", {
        "vraag_antwoorden" : vraag_antwoorden,
        "inschrijving": inschrijving,
    })


@check_rollen
def inschrijvingen_attest_download(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    inschrijving = Inschrijving.objects.get(id=inschrijving_id)
    if not inschrijving.annulatie:
        attest = genereer_deelname_attest(inschrijving_id)
        response = HttpResponse(attest, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="deelname_attest.pdf"'
        return response
    raise Http404()

@check_rollen
def inschrijvingen_attest_mail(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    inschrijving = Inschrijving.objects.get(id=inschrijving_id)
    if not inschrijving.annulatie:
        attest = genereer_deelname_attest(inschrijving_id)
        stuur_attest_mail(attest, deelnemer=inschrijving.lid)
        return redirect("inschrijving_detail", inschrijving_id=inschrijving_id)
    raise Http404()