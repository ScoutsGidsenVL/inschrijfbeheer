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

from inschrijfbeheer.mapping.providers.lid_provider import LidProvider

logger = logging.getLogger("inschrijfbeheer")

EVENT_TIJDZONE = ZoneInfo("Europe/Brussels")
VERPLICHTE_VRAGEN = {"last name", "first name", "email", "lidnummer", "date of birth"}


def parse_datetime(waarde: str | None) -> datetime | None:
    """Zet een Weez-tijdstip zonder tijdzone om naar een bewust tijdstip."""
    if not waarde:
        return None
    try:
        tijdstip = datetime.fromisoformat(waarde.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timezone.is_naive(tijdstip):
        return timezone.make_aware(tijdstip, EVENT_TIJDZONE)
    return tijdstip


@dataclass
class InschrijvingsGegevens:
    """De ledengegevens zoals de deelnemer ze zelf invulde in het formulier."""

    lidnummer: str = ""
    voornaam: str = ""
    achternaam: str = ""
    mailadres: str = ""
    geboortedatum: datetime = datetime.now()


def check_verplichte_vragen(vragen: list[dict] | None) -> tuple[bool, set]:
    """Controleert of het formulier alle verplichte vragen bevat."""
    labels = {
        (vraag.get("question") or "").lower() for vraag in vragen or [] if vraag.get("question")
    }
    return VERPLICHTE_VRAGEN.issubset(labels), VERPLICHTE_VRAGEN.difference(labels)


def bepaal_inschrijvingsgegevens(vragen: list[dict] | None) -> InschrijvingsGegevens | None:
    """Haalt de ledengegevens uit de antwoorden van een deelnemer.

    Geeft None terug wanneer één van de vier velden leeg blijft, want dan valt
    er geen deelnemer van te maken.
    """
    gegevens = InschrijvingsGegevens()
    aantal = 0

    for vraag in vragen or []:
        waarde = vraag.get("answer")
        if not waarde:
            continue

        match (vraag.get("question") or "").lower():
            case "lidnummer":
                gegevens.lidnummer = waarde
                aantal += 1
            case "last name":
                gegevens.achternaam = waarde
                aantal += 1
            case "first name":
                gegevens.voornaam = waarde
                aantal += 1
            case "email":
                gegevens.mailadres = waarde
                aantal += 1
            case "date of birth":
                gegevens.geboortedatum = waarde
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

    aantal_overeenkomsten = sum(
        [
            lidgegevens.voornaam == gegevens.voornaam,
            lidgegevens.naam == gegevens.achternaam,
            lidgegevens.emailadres == gegevens.mailadres,
            datetime.strptime(lidgegevens.geboortedatum, "%Y-%m-%d")
            == datetime.strptime(gegevens.geboortedatum, "%d/%m/%Y"),
            lidgegevens.lidnummer == gegevens.lidnummer,
        ]
    )

    if aantal_overeenkomsten < 3:
        return LidResultaat(
            foutboodschap=f"Onvoldoende matchende velden in inschrijving: {gegevens.lidnummer}"
        )

    return LidResultaat(lidgegevens=lidgegevens)
