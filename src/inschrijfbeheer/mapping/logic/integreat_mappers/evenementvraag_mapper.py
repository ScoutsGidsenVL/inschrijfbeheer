from dataclasses import dataclass

from inschrijfbeheer.models import (
    Evenement,
    EvenementVraag,
    EvenementVraagType,
    IntegreatSeminarFreeField,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .integreat_mapper import tekst


@dataclass(frozen=True)
class VraagContext:
    """Het evenement en het vraagtype zijn al bewaard."""

    evenement: Evenement
    type: EvenementVraagType


class IntegreatEvenementVraagMapper(Mapper[IntegreatSeminarFreeField, VraagContext, EvenementVraag]):
    """EvenementVraag uit een vrij veld van een seminar."""

    def map(self, bron: IntegreatSeminarFreeField, context: VraagContext) -> Doelgegevens[EvenementVraag]:
        vraag = tekst(bron.question)
        if not vraag:
            raise MappingFout(f"vrij veld {bron.oid} zonder vraagtekst")

        return Doelgegevens(
            sleutels={"id": bron.oid},
            velden={
                "type": context.type,
                "evenement": context.evenement,
                "vraag": vraag,
                "items": bron.items,
                "vereist": bron.required,
                "volgorde": bron.sortorder,
            },
        )

