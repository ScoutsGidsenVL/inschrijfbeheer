"""
Mapping van de Weezevent API naar de Django-modellen Evenement,
EvenementStatus, Categorie en Locatie, plus haal_weez_evenementen() om alles
op te halen.
"""

import logging
import re
from datetime import datetime

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
from inschrijfbeheer.mapping.mapper import (
    Mapper,
    SynchronisatieInfo,
    SynchronisatieActie,
    SynchronisatieStatus
)


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


def bepaal_lidnummer(json: str) -> str:
    for vraag_json in json:
        if vraag_json.get("label") == "Lidnummer":
            lidnummer = vraag_json.get("value")
            if lidnummer:
                return lidnummer
    raise ValueError(f"Geen lidnummer gevonden in de vragen: {json}")


class WeezSyncer(Mapper):

    def synchroniseer(self) -> SynchronisatieInfo:
        """Haalt alle Weez evenementen op en zet ze om naar Evenement modellen.
        """
        self.info.status(SynchronisatieStatus.BEZIG)
        self.sessie = maak_sessie()

        self.__synchroniseer_evenementen()

        self.sessie.close()
        self.info.status(SynchronisatieStatus.GESLAAGD)
        return self.info

    def __synchroniseer_evenementen(self) -> SynchronisatieInfo:
        overzicht = doe_weez_get(self.sessie, "events", parameters={
            "include_closed": "1", 
            "include_without_sales": "1",
        })

        weez_event_lijst = overzicht.get("events", [])
        if self.config.limiet is not None:
            weez_event_lijst = weez_event_lijst[:self.config.limiet]

        for event in weez_event_lijst:
            event_id = event["id"]
            self.synchroniseer_evenement(event_id)
        return self.info


    def synchroniseer_evenement(self, evenement_id: str, sync_deelnemers: bool = False) -> SynchronisatieInfo:
        try:
            event = doe_weez_get(self.sessie, f"event/{evenement_id}/details").get("events", {})

            categorie_data = event.get("category") or {}
            categorie = self.__haal_of_maak_categorie(categorie_data)

            locatie_data = event.get("venue") or {}
            locatie = self.__haal_of_maak_locatie(locatie_data)


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

            if sync_deelnemers:
                self.synchroniseer_inschrijvingen(evenement)

            if aangemaakt:
                self.info.registreer(Evenement, SynchronisatieActie.AANGEMAAKT)
            else:
                self.info.registreer(Evenement, SynchronisatieActie.BIJGEWERKT)
        except (KeyError, ValueError) as e:
            logger.warning("Onverwachte respons voor evenement %s: %s", evenement_id, str(e))
            self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
            return self.info

        return self.info


    def synchroniseer_inschrijvingen(self, evenement: Evenement | None = None) -> SynchronisatieInfo:
        """Synchroniseert alle deelnemers voor een bepaald evenement van Weez.

        Args:
            event_id (int): id van het evenement in Weez

        Returns:
            SynchronisatieInfo: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
        """
        evenement_prijzen = self.__haal_evenement_tarieven(evenement)

        weez_deelnemers = doe_weez_get(self.sessie, f"participant/list", parameters={
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
            lid_obj = self.__haal_of_maak_lid(lidnummer)
        
            inschrijving, aangemaakt = Inschrijving.objects.update_or_create(
                evenement=evenement,
                lid=lid_obj,
                defaults={
                    "id":inschrijving_id,
                    "tijdstip":_parse_datetime(deelnemer.get('create_date')),
                    "is_weez":True,
                    "prijs": evenement_prijzen[tarief_id],
                },
            )

            self.synchroniseer_vragen(vragen=vragen, evenement=evenement, inschrijving=inschrijving)
            
            if aangemaakt:
                self.info.registreer(Inschrijving, SynchronisatieActie.AANGEMAAKT)
            else:
                self.info.registreer(Inschrijving, SynchronisatieActie.BIJGEWERKT)
        
        return self.info

    def synchroniseer_vragen(self, evenement: Evenement | None = None, inschrijving: Inschrijving | None = None, data: dict | None = None) -> SynchronisatieInfo:
        if not data:
            return
        for index, vraag_json in enumerate(data):
            vraag, aangemaakt = EvenementVraag.objects.update_or_create(
                evenement=evenement,
                vraag=vraag_json.get("label"),
                defaults={
                    "volgorde": index,
                },
            )

            if aangemaakt:
                self.info.registreer(EvenementVraag, SynchronisatieActie.AANGEMAAKT)
            else:
                self.info.registreer(EvenementVraag, SynchronisatieActie.BIJGEWERKT)

            _, aangemaakt = InschrijvingVraagAntwoord.objects.update_or_create(
                vraag=vraag,
                inschrijving=inschrijving,
                defaults={
                    "antwoord":vraag_json.get("value"),
                },
            )

            if aangemaakt:
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.AANGEMAAKT)
            else:
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.BIJGEWERKT)

        return self.info

    def __haal_evenement_tarieven(self, evenement: Evenement) -> dict[str, int]:
        """Bepaalt de mogelijke prijzen voor een evenement en steekt deze in een dict

        Args:
            sessie (Session): sessie die de requests maakt
            evenement (Evenement): het evenement waarvoor de prijzen bepaald worden
        
        Returns:
            dict[str, int]: een mapping van een tarief id naar de prijs
        """
        evenement_prijzen_respons = doe_weez_get(self.sessie, f"tickets", parameters={
            "id_event[]": evenement.id
        })


        evenement_prijzen = {}
        for prijs_json in evenement_prijzen_respons.get("events")[0].get("tickets"):
            evenement_prijzen[prijs_json.get("id")] = prijs_json.get("price")

        return evenement_prijzen

    def __haal_of_maak_locatie(self, locatie_data: dict) -> Locatie:
        if locatie_data.get("name") or locatie_data.get("address"):
            huisnummer, straat = _split_adres(locatie_data.get("address"))
            locatie, aangemaakt = Locatie.objects.get_or_create(
                naam=locatie_data.get("name") or None,
                straat=straat,
                huisnummer=huisnummer,
                postcode=locatie_data.get("zip_code") or None,
                stad=locatie_data.get("city") or None,
                is_weez=True,
            )

            if aangemaakt:
                self.info.registreer(Locatie, SynchronisatieActie.AANGEMAAKT)

            return locatie
        return None

    def __haal_of_maak_categorie(self, categorie_data: dict) -> Categorie:
        if categorie_data.get("id") is not None:
            categorie, aangemaakt = Categorie.objects.get_or_create(
                id=str(categorie_data["id"]),
                defaults={
                    "naam": categorie_data.get("name", ""),
                    "alt_naam": categorie_data.get("name", ""),
                    "is_weez": True,
                },
            )

            if aangemaakt:
                self.info.registreer(Categorie, SynchronisatieActie.AANGEMAAKT)
            
            return categorie
        return None

    def __haal_of_maak_lid(self, lidnummer: str) -> Lid:
        lidgegevens = haal_lidgegevens(lidnummer) # TODO: check voornaam, achternaam, mail, geboortedatum, gsm (3/5) -> niet geldig = indicatie
        lid, aangemaakt = Lid.objects.get_or_create(id=lidgegevens.id, defaults={
            "voornaam": lidgegevens.voornaam,
            "achternaam": lidgegevens.naam,
            "mailadres": lidgegevens.emailadres,
        })

        if aangemaakt:
            self.info.registreer(Lid, SynchronisatieActie.AANGEMAAKT)

        return lid

