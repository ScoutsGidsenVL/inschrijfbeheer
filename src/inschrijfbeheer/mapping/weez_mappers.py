"""
Mapping van de Weezevent API naar de Django-modellen Evenement,
EvenementStatus, Categorie en Locatie, plus haal_weez_evenementen() om alles
op te halen.
"""

import logging
import re
from datetime import datetime
from dataclasses import dataclass

from inschrijfbeheer.models import (
    Categorie,
    Evenement,
    Locatie,
    Inschrijving,
    Deelnemer,
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

@dataclass
class InschrijvingsGegevens:
    lidnummer: str = ''
    voornaam: str = ''
    achternaam: str = ''
    mailadres: str = ''

def bepaal_lidnummer(json: str) -> InschrijvingsGegevens | None:
    gegevens = InschrijvingsGegevens()
    aantal = 0
    for vraag_json in json:
        match vraag_json.get("label").lower():
            case  "lidnummer":
                lidnummer: str = vraag_json.get("value")
                if lidnummer:
                    gegevens.lidnummer = lidnummer
                    aantal += 1
            case "nom":
                naam: str = vraag_json.get("value")
                if naam:
                    gegevens.achternaam = naam
                    aantal += 1
            case  "prenom":
                voornaam: str = vraag_json.get("value")
                if voornaam:
                    gegevens.voornaam = voornaam
                    aantal += 1
            case  "email":
                mail: str = vraag_json.get("value")
                if mail:
                    gegevens.mailadres = mail
                    aantal += 1
    if aantal == 4:
        return gegevens
    return None

def valideer_lidnummer(lidnummer: str) -> bool:
    return (
        lidnummer.isnumeric()
        and len(lidnummer) > 12
        and len(lidnummer) < 15 
    )

def check_verplichte_vragen(vragen) -> bool:
    verplichte_vragen = {"lidnummer", "nom", "prenom", "email"}
    found_labels = set()
    for vraag_json in vragen:
        label = vraag_json.get("label")
        if label:
            found_labels.add(label.lower())
    return verplichte_vragen.issubset(found_labels)


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
            "include_without_sales": "1",
        })

        weez_event_lijst = overzicht.get("events", [])
        if self.config.limiet is not None:
            weez_event_lijst = weez_event_lijst[:self.config.limiet]

        for event in weez_event_lijst:
            event_id = event["id"]
            self.synchroniseer_evenement(event_id, sync_deelnemers=True)
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
            "full": "1",
        })

        weez_deelnemers = weez_deelnemers.get("participants", [])

        for deelnemer in weez_deelnemers:
            vragen = deelnemer.get("answers")
            if not check_verplichte_vragen(vragen):
                self.__geen_verplichte_vraag(evenement)
                break

            inschrijving_id = str(deelnemer.get("id_participant")) + str(deelnemer.get("id_event"))
            tarief_id = deelnemer.get("id_ticket")
            inschrijving_gegevens = bepaal_lidnummer(vragen)
            lid_obj = self.__haal_of_maak_lid(inschrijving_gegevens)
        
            inschrijving, aangemaakt = Inschrijving.objects.update_or_create(
                evenement=evenement,
                lid=lid_obj,
                defaults={
                    "tijdstip":_parse_datetime(deelnemer.get('create_date')),
                    "is_weez":True,
                    "prijs": evenement_prijzen[tarief_id],
                },
            )

            self.synchroniseer_vragen(data=vragen, evenement=evenement, inschrijving=inschrijving)
            
            if aangemaakt:
                self.info.registreer(Inschrijving, SynchronisatieActie.AANGEMAAKT)
            else:
                self.info.registreer(Inschrijving, SynchronisatieActie.BIJGEWERKT)
        
        return self.info

    def synchroniseer_vragen(self, evenement: Evenement | None = None, inschrijving: Inschrijving | None = None, data: dict | None = None) -> SynchronisatieInfo:
        if not data:
            return
        if evenement and evenement.foutboodschap:
            self.__geen_verplichte_vraag(evenement)
        
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

    def __haal_of_maak_lid(self, gegevens: InschrijvingsGegevens) -> Deelnemer:
        if not valideer_lidnummer(gegevens.lidnummer):
            self.info.registreer(Deelnemer, SynchronisatieActie.AANGEMAAKT)
            
            deelnemer, _ =  Deelnemer.objects.update_or_create(
                voornaam=gegevens.voornaam,
                achternaam=gegevens.achternaam,
                mailadres=gegevens.mailadres,
                defaults={
                    "foutboodschap":f"Ongeldig lidnummer ingegeven: {gegevens.lidnummer}"
                }
            )
            return deelnemer
        try:
            lidgegevens = haal_lidgegevens(gegevens.lidnummer)
            if not (lidgegevens.voornaam == gegevens.voornaam
                 or lidgegevens.naam == gegevens.achternaam
                ):
                self.info.registreer(Deelnemer, SynchronisatieActie.AANGEMAAKT)
                 
                deelnemer, _ = Deelnemer.objects.update_or_create(
                    voornaam=gegevens.voornaam,
                    achternaam=gegevens.achternaam,
                    mailadres=gegevens.mailadres,
                    defaults={
                        "foutboodschap":f"Onvoldoende matchende velden in inschrijving: {gegevens.lidnummer}"
                    }
                )
                return deelnemer
        except Exception as fout:
            return None

        lid, aangemaakt = Deelnemer.objects.get_or_create(
            id=lidgegevens.id,
            defaults={
                "voornaam": lidgegevens.voornaam,
                "achternaam": lidgegevens.naam,
                "mailadres": lidgegevens.emailadres,
            },
        )
        if aangemaakt:
            self.info.registreer(Deelnemer, SynchronisatieActie.AANGEMAAKT)

        return lid


    def __geen_verplichte_vraag(self, evenement: Evenement) -> None:
        self.logger.warning(f"Evenement {evenement.titel} ({evenement.id}) bevat één van de  verplichte vragen niet")
        evenement.foutboodschap = "Evenement mist een verplichte vraag, inschrijvingen worden niet gesynchroniseerd"
        evenement.save()