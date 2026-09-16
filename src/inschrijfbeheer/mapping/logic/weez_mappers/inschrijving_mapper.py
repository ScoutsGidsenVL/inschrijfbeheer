from dataclasses import dataclass
from typing import Any
from django.utils import timezone

from inschrijfbeheer.models import (
    Deelnemer,
    Evenement,
    Inschrijving,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .weez_mappers import parse_datetime

@dataclass(frozen=True)
class InschrijvingContext:
    """Wat een inschrijving nodig heeft en niet in het deelnemersrecord staat."""

    evenement: Evenement
    deelnemer: Deelnemer
    deelnemertypes: dict[str, Any]


class WeezInschrijvingMapper(Mapper[dict, InschrijvingContext, Inschrijving]):
    """Inschrijving uit een deelnemersrecord.

    De prijs komt uit de tarievenlijst van het evenement, die uit een apart
    endpoint komt en daarom in de context zit.
    """

    def map(self, bron: dict, context: InschrijvingContext) -> Doelgegevens[Inschrijving]:
        tarief_id = bron.get("id_ticket")
        if tarief_id not in context.deelnemertypes:
            raise MappingFout(
                f"onbekend tarief {tarief_id} op evenement {context.evenement.id}"
            )

        annulatie_tijdstip = bron.get("removed", None)
        annulatie = None
        if annulatie_tijdstip is not None:
            annulatie = parse_datetime(annulatie_tijdstip)
            annulatie = True

        return Doelgegevens(
            sleutels={
                "id": bron.get("id"),
            },
            velden={
                "evenement": context.evenement,
                "lid": context.deelnemer,
                "tijdstip": parse_datetime(bron.get("created")),
                "prijs": bron.get("paid_price"),
                "deelnemertype": None, # TODO: bepaal deelnemertypes
                "is_weez": True,
                "annulatie": annulatie,
                "annulatie_reden": "Inschrijving verwijderd uit Weez" if annulatie else None,
                "registratie": bron.get("scanned", False)
            },
            vervang_bestaande=True,
            vervang_sleutels={
                "evenement": context.evenement,
                "lid": context.deelnemer,
            },
        )