from inschrijfbeheer.models import (
    DeelnemerType,
    IntegreatParticipantType,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper
from .integreat_mapper import tekst

class IntegreatDeelnemerTypeMapper(Mapper[IntegreatParticipantType, None, DeelnemerType]):
    """DeelnemerType uit een Integreat-deelnemerstype.

    Integreat heeft geen brongegevens voor prijs, quota of inschrijvingsperiode.
    Die placeholders staan nu in velden_bij_aanmaak. In de oude code zaten ze
    bij de defaults met timezone.now(), waardoor elke run de ingevulde prijs en
    quota wiste en de inschrijvingsperiode naar het huidige moment opschoof.
    """

    def map(self, bron: IntegreatParticipantType, context: None = None) -> Doelgegevens[DeelnemerType]:
        return Doelgegevens(
            sleutels={"id": str(bron.oid)},
            velden={"naam": tekst(bron.naam)}
        )

