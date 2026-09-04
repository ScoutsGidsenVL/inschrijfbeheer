"""Mappers van de Weezevent-brondata naar de Inschrijfbeheer-modellen.

Elke mapper hier is een zuivere functie van brondata plus context naar
Doelgegevens. Geen databankwerk, geen tellers, geen netwerkaanroepen. Wat niet
omzetbaar is, wordt een MappingFout.

De controleregels rond lidnummers staan bewust buiten de mappers, in
los_lid_op(), omdat dat synchronisatiebeleid is en geen omzetting.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
from django.utils import timezone

from django.utils import timezone

from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.models import (
    Categorie,
    Deelnemer,
    Evenement,
    EvenementVraag,
    Inschrijving,
    InschrijvingVraagAntwoord,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout

logger = logging.getLogger("inschrijfbeheer")

EVENT_TIJDZONE = ZoneInfo("Europe/Brussels")
VERPLICHTE_VRAGEN = {"lidnummer", "nom", "prenom", "email"}


def parse_datetime(waarde: str | None) -> datetime | None:
    """Zet een Weez-tijdstip zonder tijdzone om naar een bewust tijdstip."""
    if not waarde:
        return None
    try:
        tijdstip = datetime.strptime(waarde, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return timezone.make_aware(tijdstip, EVENT_TIJDZONE)


@dataclass
class InschrijvingsGegevens:
    """De ledengegevens zoals de deelnemer ze zelf invulde in het formulier."""

    lidnummer: str = ""
    voornaam: str = ""
    achternaam: str = ""
    mailadres: str = ""


def check_verplichte_vragen(vragen: list[dict] | None) -> bool:
    """Controleert of het formulier alle verplichte vragen bevat."""
    labels = {
        (vraag.get("label") or "").lower()
        for vraag in vragen or []
        if vraag.get("label")
    }
    return VERPLICHTE_VRAGEN.issubset(labels)


def bepaal_inschrijvingsgegevens(vragen: list[dict] | None) -> InschrijvingsGegevens | None:
    """Haalt de ledengegevens uit de antwoorden van een deelnemer.

    Geeft None terug wanneer één van de vier velden leeg blijft, want dan valt
    er geen deelnemer van te maken.
    """
    gegevens = InschrijvingsGegevens()
    aantal = 0

    for vraag in vragen or []:
        waarde = vraag.get("value")
        if not waarde:
            continue

        match (vraag.get("label") or "").lower():
            case "lidnummer":
                gegevens.lidnummer = waarde
                aantal += 1
            case "nom":
                gegevens.achternaam = waarde
                aantal += 1
            case "prenom":
                gegevens.voornaam = waarde
                aantal += 1
            case "email":
                gegevens.mailadres = waarde
                aantal += 1

    if aantal == len(VERPLICHTE_VRAGEN):
        return gegevens
    return None


def valideer_lidnummer(lidnummer: str) -> bool:
    """Een lidnummer is numeriek en 13 of 14 tekens lang."""
    return lidnummer.isnumeric() and 12 < len(lidnummer) < 15


@dataclass(frozen=True)
class LidResultaat:
    """Uitkomst van de ledenopzoeking, dient als context voor WeezDeelnemerMapper.

    Attributes:
        lidgegevens: de gegevens uit de ledendatabank, None als de opzoeking
            niets bruikbaars opleverde
        foutboodschap: waarom de opzoeking niets opleverde, wordt op de
            deelnemer bewaard zodat iemand het achteraf kan rechtzetten
    """

    lidgegevens: Any | None = None
    foutboodschap: str = ""


def los_lid_op(provider: LidProvider, gegevens: InschrijvingsGegevens) -> LidResultaat:
    """Zoekt het lid op en past de controleregels toe."""
    if not valideer_lidnummer(gegevens.lidnummer):
        return LidResultaat(foutboodschap=f"Ongeldig lidnummer ingegeven: {gegevens.lidnummer}")

    lidgegevens = provider.haal_op(gegevens.lidnummer)
    if lidgegevens is None:
        return LidResultaat(foutboodschap=f"Lidnummer niet gevonden: {gegevens.lidnummer}")

    # Huidige regel: minstens één van voornaam of achternaam moet overeenkomen.
    if not (
        lidgegevens.voornaam == gegevens.voornaam
        or lidgegevens.naam == gegevens.achternaam
    ):
        return LidResultaat(
            foutboodschap=f"Onvoldoende matchende velden in inschrijving: {gegevens.lidnummer}"
        )

    return LidResultaat(lidgegevens=lidgegevens)


class WeezCategorieMapper(Mapper[dict, None, Categorie]):
    """Categorie uit het `category`-blok van een evenement.

    alt_naam wordt enkel bij het aanmaken gezet, zodat een aangepaste
    alternatieve naam niet elke run overschreven raakt.
    """

    def map(self, bron: dict, context: None = None) -> Doelgegevens[Categorie]:
        if bron.get("id") is None:
            raise MappingFout("categorie zonder id")

        naam = bron.get("name", "")
        return Doelgegevens(
            sleutels={"id": str(bron["id"])},
            velden={"naam": naam, "alt_naam": naam, "is_weez": True},
        )


class WeezEvenementMapper(Mapper[dict, Categorie | None, Evenement]):
    """Evenement uit een detailrecord. De context is de al bewaarde categorie.

    De aantallen en de minimumleeftijd komen niet uit Weez en worden daarom
    enkel bij het aanmaken op nul gezet. Anders wist elke synchronisatie wat
    iemand handmatig invulde.
    """

    def map(self, bron: dict, context: Categorie | None) -> Doelgegevens[Evenement]:
        if bron.get("id") is None:
            raise MappingFout("evenement zonder id")

        periode = bron.get("period") or {}
        start = parse_datetime(periode.get("start"))
        if start is None:
            raise MappingFout(f"evenement {bron['id']} heeft geen bruikbare starttijd")
        einde = parse_datetime(periode.get("end")) or start

        locatie = bron.get("venue") or {}
        return Doelgegevens(
            sleutels={"id": str(bron["id"])},
            velden={
                "titel": bron.get("title", ""),
                "beschrijving": bron.get("description", ""),
                "starttijd": start,
                "eindtijd": einde,
                "locatie_naam": locatie.get("name"),
                "locatie_straat": locatie.get("address"),
                "locatie_stad": locatie.get("city"),
                "locatie_postcode": locatie.get("zip_code"),
                "categorie": context,
                "is_weez": True,
                "laatste_sync": timezone.now(), 
            },
        )


class WeezDeelnemerMapper(Mapper[InschrijvingsGegevens, LidResultaat, Deelnemer]):
    """Deelnemer uit de ingevulde ledengegevens plus de opzoeking.

    Leverde de opzoeking niets op, dan wordt er een deelnemer bewaard op naam
    en mailadres, met een foutboodschap. Zo gaat de inschrijving niet verloren
    en kan iemand ze achteraf rechtzetten.
    """

    def map(self, bron: InschrijvingsGegevens, context: LidResultaat) -> Doelgegevens[Deelnemer]:
        if context.lidgegevens is None:
            return Doelgegevens(
                sleutels={
                    "voornaam": bron.voornaam,
                    "achternaam": bron.achternaam,
                    "mailadres": bron.mailadres,
                },
                velden={"foutboodschap": context.foutboodschap},
            )

        lid = context.lidgegevens
        return Doelgegevens(
            sleutels={"id": lid.id},
            velden={
                "voornaam": lid.voornaam,
                "achternaam": lid.naam,
                "mailadres": lid.emailadres,
            },
        )


@dataclass(frozen=True)
class InschrijvingContext:
    """Wat een inschrijving nodig heeft en niet in het deelnemersrecord staat."""

    evenement: Evenement
    deelnemer: Deelnemer
    tarieven: dict[str, Any]


class WeezInschrijvingMapper(Mapper[dict, InschrijvingContext, Inschrijving]):
    """Inschrijving uit een deelnemersrecord.

    De prijs komt uit de tarievenlijst van het evenement, die uit een apart
    endpoint komt en daarom in de context zit.
    """

    def map(self, bron: dict, context: InschrijvingContext) -> Doelgegevens[Inschrijving]:
        tarief_id = bron.get("id_ticket")
        if tarief_id not in context.tarieven:
            raise MappingFout(
                f"onbekend tarief {tarief_id} op evenement {context.evenement.id}"
            )

        annulatie_waarde = bron.get("deleted", '0')
        annulatie = False
        if annulatie_waarde == '1':
            annulatie = True

        return Doelgegevens(
            sleutels={"id": bron.get("id_participant")},
            velden={
                "evenement": context.evenement,
                "lid": context.deelnemer,
                "tijdstip": parse_datetime(bron.get("create_date")),
                "prijs": context.tarieven[tarief_id],
                "is_weez": True,
                "annulatie": timezone.now() if annulatie else None,
                "annulatie_reden": "Inschrijving verwijderd uit Weez" if annulatie else None,
            },
        )


@dataclass(frozen=True)
class VraagContext:
    """De volgorde komt uit de positie in de antwoordenlijst, niet uit de brondata."""

    evenement: Evenement
    volgorde: int


class WeezEvenementVraagMapper(Mapper[dict, VraagContext, EvenementVraag]):
    """Vraag van een evenement, uit een antwoord van een deelnemer.

    Weez levert de vragen niet apart, enkel per deelnemer samen met het
    antwoord. Dezelfde vraag komt dus bij elke deelnemer opnieuw voorbij, en
    wordt via de sleutels ontdubbeld.
    """

    def map(self, bron: dict, context: VraagContext) -> Doelgegevens[EvenementVraag]:
        label = bron.get("label")
        if not label:
            raise MappingFout("vraag zonder label")

        return Doelgegevens(
            sleutels={"evenement": context.evenement, "vraag": label},
            velden={"volgorde": context.volgorde},
        )


@dataclass(frozen=True)
class AntwoordContext:
    """Beide verwijzingen bestaan pas nadat vraag en inschrijving bewaard zijn."""

    vraag: EvenementVraag
    inschrijving: Inschrijving


class WeezAntwoordMapper(Mapper[dict, AntwoordContext, InschrijvingVraagAntwoord]):
    """Antwoord van een deelnemer op een vraag van het evenement."""

    def map(self, bron: dict, context: AntwoordContext) -> Doelgegevens[InschrijvingVraagAntwoord]:
        return Doelgegevens(
            sleutels={"vraag": context.vraag, "inschrijving": context.inschrijving},
            velden={"antwoord": bron.get("value")},
        )