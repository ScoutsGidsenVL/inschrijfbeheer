from dataclasses import dataclass

from inschrijfbeheer.models import (
    Deelnemer,
    DeelnemerType,
    Evenement,
    Inschrijving,
    IntegreatRegistration,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper


@dataclass(frozen=True)
class InschrijvingContext:
    """Alle drie zijn al bewaard voor de inschrijving gemapt wordt."""

    evenement: Evenement
    deelnemer: Deelnemer
    deelnemertype: DeelnemerType


class IntegreatInschrijvingMapper(Mapper[IntegreatRegistration, InschrijvingContext, Inschrijving]):
    """Inschrijving uit een Integreat-registratie.

    Alleen de oid is sleutel. In de oude code stonden evenement en lid er ook
    bij, waardoor een gewijzigd evenement of lid geen bestaande rij meer vond
    en er een tweede rij met dezelfde primaire sleutel aangemaakt werd.
    """

    def map(self, bron: IntegreatRegistration, context: InschrijvingContext) -> Doelgegevens[Inschrijving]:
        return Doelgegevens(
            sleutels={"id": bron.oid},
            velden={
                "evenement": context.evenement,
                "lid": context.deelnemer,
                "deelnemertype": context.deelnemertype,
                "tijdstip": bron.tijdstip,
                "prijs": bron.price,
                "annulatie": bron.annulatie,
                "annulatie_reden": bron.canceledmotivation,
            },
        )