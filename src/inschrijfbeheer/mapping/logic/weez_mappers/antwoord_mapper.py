from dataclasses import dataclass
from inschrijfbeheer.models import (
    EvenementVraag,
    Inschrijving,
    InschrijvingVraagAntwoord,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper


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