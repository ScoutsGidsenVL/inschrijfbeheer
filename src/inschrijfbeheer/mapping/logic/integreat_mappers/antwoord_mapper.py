from dataclasses import dataclass

from inschrijfbeheer.models import (
    EvenementVraag,
    Inschrijving,
    InschrijvingVraagAntwoord,
    IntegreatRegistrationfreefield,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper


@dataclass(frozen=True)
class AntwoordContext:
    """De vraag en de inschrijving bestaan pas na hun eigen synchronisatiestap."""

    vraag: EvenementVraag
    inschrijving: Inschrijving


class IntegreatAntwoordMapper(
    Mapper[IntegreatRegistrationfreefield, AntwoordContext, InschrijvingVraagAntwoord]
):
    """InschrijvingVraagAntwoord uit een antwoord op een vrij veld."""

    def map(
        self, bron: IntegreatRegistrationfreefield, context: AntwoordContext
    ) -> Doelgegevens[InschrijvingVraagAntwoord]:
        return Doelgegevens(
            sleutels={"id": bron.oid},
            velden={
                "vraag": context.vraag,
                "inschrijving": context.inschrijving,
                "antwoord": bron.answer,
            },
        )