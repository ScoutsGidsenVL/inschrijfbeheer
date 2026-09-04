from inschrijfbeheer.models import (
    Categorie,
    IntegreatSeminarType,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .integreat_mapper import tekst, normaliseer_code

class IntegreatCategorieMapper(Mapper[IntegreatSeminarType, None, Categorie]):
    """Categorie, met de code van het seminartype als sleutel.
    """

    def map(self, bron: IntegreatSeminarType, context: None = None) -> Doelgegevens[Categorie]:
        code = normaliseer_code(bron.code)
        if not code:
            raise MappingFout("seminartype zonder code")

        naam = tekst(bron.naam)
        return Doelgegevens(
            sleutels={"id": code},
            velden={
                "naam": naam,
                "alt_naam": naam
            }
        )
