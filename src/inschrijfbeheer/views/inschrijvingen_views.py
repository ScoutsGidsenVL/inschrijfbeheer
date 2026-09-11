"""Module die de views bevat voor alle inschrijvingen gerelateerde zaken

## Functies:
    **inschrijvingen_detail:** Geeft een view voor het tonen van alle details van een inschrijving
"""
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseNotFound
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction
import logging
from typing import Iterable

from inschrijfbeheer.mapping.logic.weez_mappers.deelnemer_mapper import WeezDeelnemerMapper
from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import LidResultaat
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.models import Inschrijving, InschrijvingVraagAntwoord, Deelnemer
from inschrijfbeheer.utils.auth import check_rollen
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mail
from inschrijfbeheer.utils.scanner import scan_inschrijving
from inschrijfbeheer.utils.weez_api import maak_sessie
from inschrijfbeheer.mapping.logic.weez_mappers import weez_sleutel_van, bepaal_inschrijvingsgegevens, los_lid_op

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
        form_data = {}
        for vraag_antwoord in vraag_antwoorden:
            nieuw_antwoord = request.POST.get(f"antwoord_{vraag_antwoord.id}", "").strip()
            vraag_antwoord.antwoord = nieuw_antwoord
            form_data[weez_sleutel_van(vraag_antwoord.vraag)] = nieuw_antwoord

        stuur_weezevent_update(inschrijving, form_data)

        with transaction.atomic():
            InschrijvingVraagAntwoord.objects.bulk_update(vraag_antwoorden, ["antwoord"])
            resultaat = herbepaal_deelnemer(inschrijving, vraag_antwoorden)

        if resultaat.foutboodschap:
            messages.warning(request, resultaat.foutboodschap)
        else:
            messages.success(request, "De gegevens kloppen nu met de ledendatabank.")

        return redirect("inschrijving_vragen", inschrijving_id=inschrijving_id)

    return render(request, "inschrijvingen/inschrijvingen_vragen.html", {
        "vraag_antwoorden": vraag_antwoorden,
        "inschrijving": inschrijving,
    })


@transaction.atomic
def herbepaal_deelnemer(
    inschrijving: Inschrijving,
    vraag_antwoorden: Iterable[InschrijvingVraagAntwoord],
    provider: LidProvider | None = None,
) -> LidResultaat:
    """Bepaalt de deelnemer van een inschrijving opnieuw uit de huidige antwoorden.

    Draait dezelfde controle als de synchronisatie. Levert de opzoeking nu een
    lid op, dan verhuist de inschrijving naar de deelnemer van dat lid, die al
    kan bestaan. Klopt ze niet meer, dan komt er een deelnemer met een
    foutboodschap en verhuist de inschrijving daarnaartoe. Blijft de deelnemer
    dezelfde, dan wordt enkel de foutboodschap bijgewerkt.

    Args:
        inschrijving (Inschrijving): inschrijving waarvan de deelnemer herbepaald wordt
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
        _bewaar_foutboodschap(inschrijving.lid, resultaat.foutboodschap)
        return resultaat

    try:
        resultaat = los_lid_op(provider or LidProvider(), gegevens)
    except ValueError:
        resultaat = LidResultaat(
            foutboodschap=f"Onleesbare geboortedatum: {gegevens.geboortedatum}"
        )

    doel = WeezDeelnemerMapper().map(gegevens, resultaat)
    deelnemer, _ = Deelnemer.objects.update_or_create(**doel.sleutels, defaults=doel.velden)
    _bewaar_foutboodschap(deelnemer, resultaat.foutboodschap)

    oude_deelnemer = inschrijving.lid
    if deelnemer.pk != oude_deelnemer.pk:
        inschrijving.lid = deelnemer
        inschrijving.save(update_fields=["lid"])
        logger.info(
            "Inschrijving %s verhangen van deelnemer %s naar %s",
            inschrijving.id, oude_deelnemer.pk, deelnemer.pk,
        )
        _ruim_deelnemer_op(oude_deelnemer)

    return resultaat


def _bewaar_foutboodschap(deelnemer: Deelnemer, foutboodschap: str) -> None:
    """Zet de foutboodschap enkel weg als ze verandert."""
    if (deelnemer.foutboodschap or "") != foutboodschap:
        deelnemer.foutboodschap = foutboodschap
        deelnemer.save(update_fields=["foutboodschap"])


def _ruim_deelnemer_op(deelnemer: Deelnemer) -> None:
    """Verwijdert een achtergebleven deelnemer die enkel een foutboodschap was.

    Een deelnemer die aan een lid hangt blijft staan, want dat model bestaat
    net om SOAP-calls naar de GA uit te sparen. Een rij die alleen ontstond
    omdat de opzoeking mislukte, heeft zonder inschrijving geen nut meer.
    """
    if not deelnemer.foutboodschap:
        return
    if Inschrijving.objects.filter(lid=deelnemer).exists():
        return

    logger.info("Deelnemer %s verwijderd, geen inschrijving verwijst er nog naar", deelnemer.pk)
    deelnemer.delete()


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


@require_http_methods(['PATCH'])
@transaction.atomic
def inschrijvingen_registreren(request: HttpRequest, inschrijving_id: str) -> HttpResponse:
    inschrijving = Inschrijving.objects.get(id=inschrijving_id)

    resultaat = scan_inschrijving(inschrijving)
    if resultaat.gelukt:
        inschrijving.registratie = True
        inschrijving.save()
        return HttpResponse()

    logger.warning("Aanwezig zetten deelnemer gefaald")
    return HttpResponseNotFound()