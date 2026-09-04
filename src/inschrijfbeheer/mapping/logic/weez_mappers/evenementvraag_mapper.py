from dataclasses import dataclass

from inschrijfbeheer.models import (

    Evenement,
    EvenementVraag,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout


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