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
                "prijs": context.deelnemertypes[tarief_id]["prijs"],
                "deelnemertype": context.deelnemertypes[tarief_id]["type"],
                "is_weez": True,
                "annulatie": timezone.now() if annulatie else None,
                "annulatie_reden": "Inschrijving verwijderd uit Weez" if annulatie else None,
            },
        )