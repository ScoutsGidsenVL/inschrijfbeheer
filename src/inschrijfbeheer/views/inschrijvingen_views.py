"""Module die de views bevat voor alle inschrijvingen gerelateerde zaken

## Functies:
    **inschrijvingen_detail:** Geeft een view voor het tonen van alle details van een inschrijving
"""
import json

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse
from django.contrib import messages
import logging
from django.views.decorators.http import require_http_methods

from inschrijfbeheer.models import Inschrijving, InschrijvingVraagAntwoord
from inschrijfbeheer.utils.auth import check_rollen
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mail
from inschrijfbeheer.tasks import defer_synchroniseer_inschrijvingen
from inschrijfbeheer.utils.scanner import WeezScanFout, stuur_scan
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


@check_rollen
@require_http_methods(["PATCH"])
def inschrijvingen_registreren(request):
    """Zet de aanwezigheid van meerdere inschrijvingen in één keer en stuur de scans door.

    Body: {"inschrijving_ids": [1, 2, 3], "aanwezig": true}

    Antwoord: {"resultaten": [
        {"id": 1, "aanwezig": bool of null, "scan_gelukt": bool, "boodschap": str}, ...
    ]}
    Een niet-gevonden id krijgt "aanwezig": null en "scan_gelukt": false terug.
    """
    try:
        gegevens = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"boodschap": "Stuur geldige JSON mee."}, status=400)

    inschrijving_ids = gegevens.get("inschrijving_ids")
    if not isinstance(inschrijving_ids, list) or not inschrijving_ids:
        return JsonResponse(
            {"boodschap": "Het veld inschrijving_ids moet een niet-lege lijst zijn."},
            status=400,
        )
    if not all(isinstance(inschrijving_id, int) for inschrijving_id in inschrijving_ids):
        return JsonResponse(
            {"boodschap": "inschrijving_ids moet een lijst van getallen zijn."}, status=400
        )

    aanwezig = gegevens.get("aanwezig", True)
    if not isinstance(aanwezig, bool):
        return JsonResponse(
            {"boodschap": "Het veld aanwezig moet true of false zijn."}, status=400
        )

    inschrijvingen = {
        inschrijving.id: inschrijving
        for inschrijving in Inschrijving.objects.filter(
            pk__in=inschrijving_ids, is_weez=False
        )
    }

    resultaten = []
    for inschrijving_id in inschrijving_ids:
        inschrijving = inschrijvingen.get(str(inschrijving_id))
        if inschrijving is None:
            resultaten.append(
                {
                    "id": inschrijving_id,
                    "aanwezig": None,
                    "scan_gelukt": False,
                    "boodschap": "Inschrijving niet gevonden.",
                }
            )
            continue

        inschrijving.registratie = aanwezig
        inschrijving.save(update_fields=["registratie"])

        scan_gelukt = True
        boodschap = ""
        try:
            stuur_scan(inschrijving.weez_barcode, status=1 if aanwezig else 0)
        except WeezScanFout as fout:
            scan_gelukt = False
            boodschap = str(fout)
            logger.warning(
                "Scan voor inschrijving %s mislukte: %s", inschrijving.pk, fout
            )

        resultaten.append(
            {
                "id": inschrijving.pk,
                "aanwezig": inschrijving.aanwezig,
                "scan_gelukt": scan_gelukt,
                "boodschap": boodschap,
            }
        )

    return JsonResponse({"resultaten": resultaten})