"""
Mapping van de Weezevent API naar de Django-modellen Evenement,
EvenementStatus, Categorie en Locatie, plus haal_weez_evenementen() om alles
op te halen.
"""

import os
import re
from datetime import datetime
from dotenv import load_dotenv

from requests import Session

from inschrijfbeheer.models import (
    Categorie,
    Evenement,
    Locatie,
    Inschrijving,
    Lid,
    EvenementVraag,
    InschrijvingVraagAntwoord
)
from inschrijfbeheer.utils.weez_api import doe_weez_get
from inschrijfbeheer.utils.soap import haal_lidgegevens


from zoneinfo import ZoneInfo
from django.utils import timezone

QueryInfoType = tuple[int, int, int]

EVENT_TIJDZONE = ZoneInfo("Europe/Brussels")

def _parse_datetime(waarde):
    if not waarde:
        return None

    try:
        tijdstip = datetime.strptime(waarde, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    return timezone.make_aware(tijdstip, EVENT_TIJDZONE)


def _split_adres(adres: str | None) -> tuple[str | None, str | None]:
    """Splitst een adresstring ('110 rue des Poissonniers') in huisnummer en straat.

    Heuristiek: het eerste cijferblok is het huisnummer, de rest is de straat.
    Werkt niet voor adressen waar het huisnummer na de straatnaam staat.
    Controleer dit steekproefsgewijs op echte data."""
    if not adres:
        return None, None
    match = re.match(r"^\s*(\d+\w*)\s+(.*)$", adres)
    if not match:
        return None, adres
    huisnummer, straat = match.groups()
    return huisnummer, straat


def map_evenement_detail(payload: dict) -> tuple[Evenement, bool]:
    """Zet de respons van de detail-route om naar Evenement, inclusief
    Locatie en Categorie. Zie de moduledocstring voor wat (nog) niet
    gemapt wordt en waarom."""
    event = payload["events"]

    categorie = None
    cat_data = event.get("category") or {}
    if cat_data.get("id") is not None:
        categorie, _ = Categorie.objects.update_or_create(
            id=str(cat_data["id"]),
            defaults={
                "naam": cat_data.get("name", ""),
                "alt_naam": cat_data.get("name", ""),
                "is_weez": True,
            },
        )

    locatie = None
    venue = event.get("venue") or {}
    if venue.get("name") or venue.get("address"):
        huisnummer, straat = _split_adres(venue.get("address"))
        locatie, _ = Locatie.objects.get_or_create(
            naam=venue.get("name") or None,
            straat=straat,
            huisnummer=huisnummer,
            postcode=venue.get("zip_code") or None,
            stad=venue.get("city") or None,
            is_weez=True,
        )

    periode = event.get("period") or {}
    starttijd = _parse_datetime(periode.get("start"))
    eindtijd = _parse_datetime(periode.get("end")) or starttijd

    evenement, aangemaakt = Evenement.objects.update_or_create(
        id=str(event["id"]),
        defaults={
            "titel": event.get("title", ""),
            "beschrijving": event.get("description", ""),
            "starttijd": starttijd,
            "eindtijd": eindtijd,
            "locatie": locatie,
            "categorie": categorie,
            "min_deelnemers": 0,
            "max_deelnemers": 0,
            "aantal_zelfde_groep": 0,
            "min_leeftijd": 0,
            "is_weez": True,
        },
    )

    return evenement, aangemaakt

def bepaal_lidnummer(json: str) -> str:
    for vraag_json in json:
        if vraag_json.get("label") == "Lidnummer":
            lidnummer = vraag_json.get("value")
            if lidnummer:
                return lidnummer
    raise ValueError(f"Geen lidnummer gevonden in de vragen: {json}")

def haal_weez_deelnemers(sessie: Session, evenement: Evenement) -> QueryInfoType:
    """Synchroniseert alle deelnemers voor een bepaald evenement van Weez.

    Args:
        sessie (Session): sessie voor het uitvoeren van de requests
        event_id (int): id van het evenement in Weez

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    evenement_prijzen_respons = doe_weez_get(sessie, f"tickets", parameters={
        "id_event[]": evenement.id
    })
    evenement_prijzen_respons.raise_for_status()
    evenement_prijzen_respons = evenement_prijzen_respons.json()

    evenement_prijzen = {}
    for prijs_json in evenement_prijzen_respons.get("events")[0].get("tickets"):
        evenement_prijzen[prijs_json.get("id")] = prijs_json.get("price")

    weez_deelnemers_respons = doe_weez_get(sessie, f"participant/list", parameters={
        "id_event[]": evenement.id,
        "include_deleted": "1",
        "full": "1",
    })
    weez_deelnemers_respons.raise_for_status()
    weez_deelnemers = weez_deelnemers_respons.json()

    weez_deelnemers = weez_deelnemers.get("participants", [])

    for deelnemer in weez_deelnemers:
        inschrijving_id = str(deelnemer.get("id_participant")) + str(deelnemer.get("id_event"))
        tarief_id = deelnemer.get("id_ticket")
        vragen = deelnemer.get("answers")

        lid = haal_lidgegevens(bepaal_lidnummer(vragen))
        lid_obj, _ = Lid.objects.get_or_create(id=lid.id, defaults={
            "voornaam": lid.voornaam,
            "achternaam": lid.naam,
            "mailadres": lid.emailadres,
        })
    
        inschrijving, is_nieuw = Inschrijving.objects.update_or_create(
            evenement=evenement,
            lid=lid_obj,
            defaults={
                "id":inschrijving_id,
                "tijdstip":_parse_datetime(deelnemer.get('create_date')),
                "is_weez":True,
                "prijs": evenement_prijzen[tarief_id],
            },
        )

        if vragen:
            for index, vraag_json in enumerate(vragen):
                vraag, vraag_is_nieuw = EvenementVraag.objects.get_or_create(
                    evenement=evenement,
                    vraag=vraag_json.get("label"),
                    defaults={
                        "volgorde": index,
                    },
                )

                _, _ = InschrijvingVraagAntwoord.objects.get_or_create(
                    vraag=vraag,
                    inschrijving=inschrijving,
                    defaults={
                        "antwoord":vraag_json.get("value"),
                    },
                )

                if vraag_is_nieuw:
                    aangemaakt += 2
                else:
                    bijgewerkt += 2
        
        if is_nieuw:
            aangemaakt +=1
        else:
            bijgewerkt += 1
    
    return aangemaakt, bijgewerkt, overgeslagen

def haal_weez_evenementen(sessie: Session, limiet: None | int = None) -> QueryInfoType:
    """Haalt alle Weezevent-evenementen op en zet ze om naar Evenement-records.

    Stap 1: GET {BASE_URL}/event geeft de lijst van evenementen met hun id's.
    Stap 2: voor elk id een GET naar {BASE_URL}/event/<id> voor de volledige
            details.
    Stap 3: elk detail-antwoord wordt via map_evenement_detail() weggeschreven.

    Als een enkele detail-aanroep faalt, wordt dat gelogd en gaat de functie
    verder met de overige id's, in plaats van de volledige import te laten
    mislukken. Let op: als /event gepagineerd is, haalt deze functie enkel de
    eerste pagina op, breid uit met paginering indien nodig.
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    overzicht_resp = doe_weez_get(sessie, "events", parameters={
        "include_closed": "1", 
        "include_without_sales": "1",
    })
    overzicht_resp.raise_for_status()
    overzicht = overzicht_resp.json()

    weez_event_lijst = overzicht.get("events", [])
    if limiet is not None:
        weez_event_lijst = weez_event_lijst[:limiet]

    evenementen: list[Evenement] = []
    for event in weez_event_lijst:
        event_id = event["id"]
        try:
            detail_resp = doe_weez_get(sessie, f"event/{event_id}/details")
            detail_resp.raise_for_status()
            detail_payload = detail_resp.json()
            evenement, is_nieuw = map_evenement_detail(detail_payload)

            nieuwe_deelnemers, bijgewerkte_deelnemers, overgeslagen_deelnemers = haal_weez_deelnemers(sessie, evenement)

            aangemaakt += nieuwe_deelnemers
            bijgewerkt += bijgewerkte_deelnemers
            overgeslagen += overgeslagen_deelnemers

            if is_nieuw:
                aangemaakt += 1
            else:
                bijgewerkt += 1
        except (KeyError, ValueError) as e:
            print("Onverwachte respons voor evenement %s: %s", event_id, str(e))
            overgeslagen += 1
            continue

    return aangemaakt, bijgewerkt, overgeslagen