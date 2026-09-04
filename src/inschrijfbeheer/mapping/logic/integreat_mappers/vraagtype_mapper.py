from dataclasses import dataclass

from inschrijfbeheer.models import (
    EvenementVraagType,
    IntegreatSeminarFreeFieldType,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .integreat_mapper import normaliseer_code

class IntegreatVraagTypeMapper(Mapper[IntegreatSeminarFreeFieldType, None, EvenementVraagType]):
    """EvenementVraagType, ontdubbeld op naam.

    In de oude code hoorden items_vereist en items_toegestaan bij de
    opzoeksleutels, waardoor een gewijzigd aantal een tweede type met dezelfde
    naam aanmaakte. Nu zijn ze gewone velden.
    """

    def map(
        self, bron: IntegreatSeminarFreeFieldType, context: None = None
    ) -> Doelgegevens[EvenementVraagType]:
        naam = normaliseer_code(bron.code)
        if not naam:
            raise MappingFout("vraagtype zonder code")

        return Doelgegevens(
            sleutels={"naam": naam},
            velden={
                "items_vereist": bron.itemsrequired,
                "items_toegestaan": bron.itemsallowed,
            },
        )
