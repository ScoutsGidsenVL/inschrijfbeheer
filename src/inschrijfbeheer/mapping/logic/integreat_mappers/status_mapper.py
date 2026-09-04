from inschrijfbeheer.models import (
    EvenementStatus,
    IntegreatSeminarStatus,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper
from .integreat_mapper import tekst

class IntegreatStatusMapper(Mapper[IntegreatSeminarStatus, None, EvenementStatus]):
    """EvenementStatus, ontdubbeld op beschrijving.
    """

    def map(self, bron: IntegreatSeminarStatus, context: None = None) -> Doelgegevens[EvenementStatus]:
        return Doelgegevens(sleutels={"beschrijving": tekst(bron.beschrijving)})



