"""Module die de views bevat voor alle inschrijvingen gerelateerde zaken

## Functies:
    **inschrijvingen_detail:** Geeft een view voor het tonen van alle details van een inschrijving
"""
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404
from django.contrib import messages
import logging

from inschrijfbeheer.models import Inschrijving, InschrijvingVraagAntwoord
from inschrijfbeheer.utils.auth import check_rollen
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mail
from inschrijfbeheer.tasks import defer_synchroniseer_inschrijvingen
from inschrijfbeheer.utils.weez_api import maak_sessie, doe_weez_patch
from inschrijfbeheer.mapping.logic.weez_mappers import weez_sleutel_van

logger = logging.getLogger("inschrijfbeheer")

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
    inschrijving = Inschrijving.objects.select_related("lid", "evenement", "deelnemertype").get(id=inschrijving_id)
    vraag_antwoorden = InschrijvingVraagAntwoord.objects.filter(inschrijving=inschrijving_id).select_related("vraag", "vraag__type").order_by("vraag__volgorde")

    if request.method == "POST":
        if inschrijving.evenement.is_weez:
            form_data = {}
            for vraag_antwoord in vraag_antwoorden:
                nieuw_antwoord = request.POST.get(f"antwoord_{vraag_antwoord.id}", "").strip()
                vraag_antwoord.antwoord = nieuw_antwoord
                form_data[weez_sleutel_van(vraag_antwoord.vraag)] = nieuw_antwoord

            stuur_weezevent_update(inschrijving, form_data)

            defer_synchroniseer_inschrijvingen(evenement_id=inschrijving.evenement.id)

        return redirect("inschrijving_vragen", inschrijving_id=inschrijving_id)

    return render(request, "inschrijvingen/inschrijvingen_vragen.html", {
        "vraag_antwoorden": vraag_antwoorden,
        "inschrijving": inschrijving,
    })


def stuur_weezevent_update(inschrijving: Inschrijving, antwoorden: dict[str, str]) -> None:
    payload = {
        "participants": [
            {
                "id_participant": inschrijving.id,
                "id_evenement": inschrijving.evenement.id,
                "id_billet": inschrijving.deelnemertype.id,
                "email": antwoorden.get("email", inschrijving.lid.mailadres),
                "nom": antwoorden.get("nom", inschrijving.lid.achternaam),
                "prenom": antwoorden.get("prenom", inschrijving.lid.voornaam),
                "form": antwoorden,
            }
        ]
    }

    sessie = maak_sessie()
    doe_weez_patch(sessie, "v3/participants", payload)


@check_rollen
def inschrijvingen_attest_download(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    """Functie voor het downloaden van een attest als een deelnemer aanwezig was.
    Controleert of de deelnemer aanwezig was en geldig is

    Deze functie wordt gebruikt voor `/inschrijvingen/<id>/attest/download`

    Args:
        request (HttpRequest): HTTP request voor de pagina
        inschrijving_id (str): id van de inschrijving

    Returns:
        HttpResponse: pdf van het attest
    
    Raises:
        Http404: indien deelnemer of inschrijving niet geldig was wordt het attest niet gevonden
    """
    inschrijving = Inschrijving.objects.select_related("lid").get(id=inschrijving_id)
    if inschrijving.aanwezig:
        attest = genereer_deelname_attest(inschrijving_id)
        response = HttpResponse(attest, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="deelname_attest.pdf"'
        return response
    raise Http404()

@check_rollen
def inschrijvingen_attest_mail(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    """Functie voor het mailen van een attest als een deelnemer aanwezig was.
    Controleert of de deelnemer aanwezig was en geldig is

    Deze functie wordt gebruikt voor `/inschrijvingen/<id>/attest/mail`

    Args:
        request (HttpRequest): HTTP request voor de pagina
        inschrijving_id (str): id van de inschrijving

    Returns:
        HttpResponse: redirect naar de inschrijving pagina
    
    Raises:
        Http404: indien deelnemer of inschrijving niet geldig was wordt het attest niet gevonden
    """
    inschrijving = Inschrijving.objects.get(id=inschrijving_id)
    if inschrijving.aanwezig:
        attest = genereer_deelname_attest(inschrijving_id)
        stuur_attest_mail(attest, deelnemer=inschrijving.lid)
        messages.success(request, "Het attest werd succesvol verstuurd.")
        return redirect("inschrijving_detail", inschrijving_id=inschrijving_id)
    raise Http404()