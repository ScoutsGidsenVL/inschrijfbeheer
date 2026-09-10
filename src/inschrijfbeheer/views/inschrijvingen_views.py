"""Module die de views bevat voor alle inschrijvingen gerelateerde zaken

## Functies:
    **inschrijvingen_detail:** Geeft een view voor het tonen van alle details van een inschrijving
"""
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404
from django.contrib import messages

from typing import Iterable

from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import LidResultaat
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.models import Inschrijving, InschrijvingVraagAntwoord, Deelnemer
from inschrijfbeheer.utils.auth import check_rollen
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mail
from inschrijfbeheer.utils.weez_api import maak_sessie, doe_weez_patch
from inschrijfbeheer.mapping.logic.weez_mappers import weez_sleutel_van, bepaal_inschrijvingsgegevens, los_lid_op

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
        form_data = {}
        for vraag_antwoord in vraag_antwoorden:
            nieuw_antwoord = request.POST.get(f"antwoord_{vraag_antwoord.id}", "").strip()
            vraag_antwoord.antwoord = nieuw_antwoord
            form_data[weez_sleutel_van(vraag_antwoord.vraag)] = nieuw_antwoord

        stuur_weezevent_update(inschrijving, form_data)
        InschrijvingVraagAntwoord.objects.bulk_update(vraag_antwoorden, ["antwoord"])
        
        resultaat = controleer_deelnemer(inschrijving.lid, vraag_antwoorden)
        if resultaat.foutboodschap:
            messages.warning(request, resultaat.foutboodschap)
        else:
            messages.success(request, "De gegevens kloppen nu met de ledendatabank.")
        return redirect("inschrijving_vragen", inschrijving_id=inschrijving_id)

    return render(request, "inschrijvingen/inschrijvingen_vragen.html", {
        "vraag_antwoorden": vraag_antwoorden,
        "inschrijving": inschrijving,
    })


def controleer_deelnemer(
    deelnemer: Deelnemer,
    vraag_antwoorden: Iterable[InschrijvingVraagAntwoord],
    provider: LidProvider | None = None,
) -> LidResultaat:
    """Controleert de ledengegevens van een deelnemer opnieuw.

    Draait dezelfde controle als de synchronisatie, maar op de antwoorden zoals
    ze nu bij de deelnemer staan. Klopt alles, dan wordt de foutboodschap
    leeggemaakt, anders komt de nieuwe reden ervoor in de plaats.

    Args:
        deelnemer (Deelnemer): deelnemer waarvan de foutboodschap bijgewerkt wordt
        vraag_antwoorden (Iterable[InschrijvingVraagAntwoord]): antwoorden van de
            deelnemer, met hun vraag ingeladen
        provider (LidProvider | None, optional): bron voor de ledengegevens.

    Returns:
        LidResultaat: uitkomst van de opzoeking, met een lege foutboodschap als
            de deelnemer nu wel klopt
    """
    vragen = [
        {"label": vraag_antwoord.vraag.vraag, "value": vraag_antwoord.antwoord}
        for vraag_antwoord in vraag_antwoorden
    ]

    gegevens = bepaal_inschrijvingsgegevens(vragen)
    if gegevens is None:
        resultaat = LidResultaat(
            foutboodschap="Onvolledige ledengegevens, vul lidnummer, naam, voornaam, mailadres en geboortedatum in"
        )
    else:
        try:
            resultaat = los_lid_op(provider or LidProvider(), gegevens)
        except ValueError:
            resultaat = LidResultaat(
                foutboodschap=f"Onleesbare geboortedatum: {gegevens.geboortedatum}"
            )

    if deelnemer.foutboodschap != resultaat.foutboodschap:
        deelnemer.foutboodschap = resultaat.foutboodschap
        deelnemer.save(update_fields=["foutboodschap"])

    return resultaat


def stuur_weezevent_update(inschrijving: Inschrijving, form_data: dict) -> None:
    payload = {
        "participants": [
            {
                "id_participant": inschrijving.id,
                "id_evenement": inschrijving.evenement.id,
                "id_billet": inschrijving.deelnemertype.id,
                "email": inschrijving.lid.mailadres,
                "nom": inschrijving.lid.achternaam,
                "prenom": inschrijving.lid.voornaam,
                "form": form_data,
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
    if not inschrijving.annulatie and not inschrijving.lid.foutboodschap:
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
    if not inschrijving.annulatie:
        attest = genereer_deelname_attest(inschrijving_id)
        stuur_attest_mail(attest, deelnemer=inschrijving.lid)
        messages.success(request, "Het attest werd succesvol verstuurd.")
        return redirect("inschrijving_detail", inschrijving_id=inschrijving_id)
    raise Http404()