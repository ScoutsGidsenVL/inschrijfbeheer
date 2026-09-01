"""
Mapping van de Weezevent API naar de Django-modellen Evenement,
EvenementStatus, Categorie en Locatie, plus haal_weez_evenementen() om alles
op te halen.
"""

import logging
import re
from datetime import datetime

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
from inschrijfbeheer.utils.weez_api import doe_weez_get, maak_sessie
from inschrijfbeheer.utils.soap import haal_lidgegevens
from inschrijfbeheer.mapping.mapper import Mapper, SynchronisatieInfo


from zoneinfo import ZoneInfo
from django.utils import timezone

QueryInfoType = tuple[int, int, int]
logger = logging.getLogger("inschrijfbeheer")

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

def haal_of_maak_categorie(categorie_data: dict) -> Categorie:
    if categorie_data.get("id") is not None:
        categorie, _ = Categorie.objects.get_or_create(
            id=str(categorie_data["id"]),
            defaults={
                "naam": categorie_data.get("name", ""),
                "alt_naam": categorie_data.get("name", ""),
                "is_weez": True,
            },
        )
        return categorie
    return None

def haal_of_maak_locatie(locatie_data: dict) -> Locatie:
    if locatie_data.get("name") or locatie_data.get("address"):
        huisnummer, straat = _split_adres(locatie_data.get("address"))
        locatie, _ = Locatie.objects.get_or_create(
            naam=locatie_data.get("name") or None,
            straat=straat,
            huisnummer=huisnummer,
            postcode=locatie_data.get("zip_code") or None,
            stad=locatie_data.get("city") or None,
            is_weez=True,
        )
        return locatie
    return None

def map_evenement_detail(payload: dict) -> tuple[Evenement, bool]:
    """Zet de respons van de detail-route om naar Evenement, inclusief
    Locatie en Categorie. Zie de moduledocstring voor wat (nog) niet
    gemapt wordt en waarom."""
    event = payload["events"]

    categorie_data = event.get("category") or {}
    categorie = haal_of_maak_categorie(categorie_data)

    locatie_data = event.get("venue") or {}
    locatie = haal_of_maak_locatie(locatie_data)


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

def haal_evenement_tarieven(sessie: Session, evenement: Evenement) -> dict[str, int]:
    """Bepaalt de mogelijke prijzen voor een evenement en steekt deze in een dict

    Args:
        sessie (Session): sessie die de requests maakt
        evenement (Evenement): het evenement waarvoor de prijzen bepaald worden
    
    Returns:
        dict[str, int]: een mapping van een tarief id naar de prijs
    """
    evenement_prijzen_respons = doe_weez_get(sessie, f"tickets", parameters={
        "id_event[]": evenement.id
    })


    evenement_prijzen = {}
    for prijs_json in evenement_prijzen_respons.get("events")[0].get("tickets"):
        evenement_prijzen[prijs_json.get("id")] = prijs_json.get("price")

    return evenement_prijzen

def haal_of_maak_lid(lidnummer: str) -> Lid:
        lid = haal_lidgegevens(lidnummer)
        lid_obj, _ = Lid.objects.get_or_create(id=lid.id, defaults={
            "voornaam": lid.voornaam,
            "achternaam": lid.naam,
            "mailadres": lid.emailadres,
        })

def verwerk_vragen(vragen, evenement: Evenement, inschrijving: Inschrijving):
    if not vragen:
        return
    for index, vraag_json in enumerate(vragen):
        vraag, _ = EvenementVraag.objects.get_or_create(
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

def haal_weez_deelnemers(sessie: Session, evenement: Evenement) -> QueryInfoType:
    """Synchroniseert alle deelnemers voor een bepaald evenement van Weez.

    Args:
        sessie (Session): sessie voor het uitvoeren van de requests
        event_id (int): id van het evenement in Weez

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    evenement_prijzen = haal_evenement_tarieven(sessie, evenement)

    weez_deelnemers = doe_weez_get(sessie, f"participant/list", parameters={
        "id_event[]": evenement.id,
        "include_deleted": "1",
        "full": "1",
    })
    
    weez_deelnemers = weez_deelnemers.get("participants", [])

    for deelnemer in weez_deelnemers:
        inschrijving_id = str(deelnemer.get("id_participant")) + str(deelnemer.get("id_event"))
        tarief_id = deelnemer.get("id_ticket")
        vragen = deelnemer.get("answers")
        lidnummer = bepaal_lidnummer(vragen)
        lid_obj = haal_of_maak_lid(lidnummer)
    
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

        verwerk_vragen(vragen=vragen, evenement=evenement, inschrijving=inschrijving)
        
        if is_nieuw:
            aangemaakt +=1
        else:
            bijgewerkt += 1
    
    return aangemaakt, bijgewerkt, overgeslagen

class WeezSyncer(Mapper):

    def synchroniseer(self) -> SynchronisatieInfo:
        """Haalt alle Weez evenementen op en zet ze om naar Evenement modellen.
        """
        sessie = maak_sessie()
        aangemaakt = bijgewerkt = overgeslagen = 0

        overzicht = doe_weez_get(sessie, "events", parameters={
            "include_closed": "1", 
            "include_without_sales": "1",
        })

        weez_event_lijst = overzicht.get("events", [])
        if self.config.limiet is not None:
            weez_event_lijst = weez_event_lijst[:self.config.limiet]

        evenementen: list[Evenement] = []
        for event in weez_event_lijst:
            event_id = event["id"]
            try:
                detail_payload = doe_weez_get(sessie, f"event/{event_id}/details")
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
                logger.warning("Onverwachte respons voor evenement %s: %s", event_id, str(e))
                overgeslagen += 1
                continue

        sessie.close()
        return aangemaakt, bijgewerkt, overgeslagen