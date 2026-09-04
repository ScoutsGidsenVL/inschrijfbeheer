from typing import Any

from inschrijfbeheer.models import (
    Deelnemer,
    IntegreatParticipant,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .integreat_mapper import tekst

class IntegreatDeelnemerMapper(Mapper[IntegreatParticipant, Any, Deelnemer]):
    """Deelnemer uit een Integreat-deelnemer plus de ledenopzoeking.

    De context is het LidGegevens-object uit de SOAP-opzoeking, of None als de
    opzoeking niets opleverde. Anders dan bij Weez wordt er hier geen deelnemer
    met foutboodschap bewaard, want bij een migratie wil je geen half
    ingevulde leden aanmaken. De inschrijving wordt dan overgeslagen.
    """

    def map(self, bron: IntegreatParticipant, context: Any) -> Doelgegevens[Deelnemer]:
        lidnummer = tekst(bron.lid_id)
        if not lidnummer:
            raise MappingFout("deelnemer zonder lidnummer")
        if context is None:
            raise MappingFout(f"geen ledengegevens gevonden voor lidnummer {lidnummer}")

        return Doelgegevens(
            sleutels={"id": lidnummer},
            velden={
                "voornaam": tekst(context.voornaam),
                "achternaam": tekst(context.naam),
                "mailadres": tekst(context.emailadres),
            },
        )


