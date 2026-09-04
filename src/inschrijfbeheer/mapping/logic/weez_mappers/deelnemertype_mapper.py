from inschrijfbeheer.mapping.logic import Mapper, Doelgegevens, MappingFout
from inschrijfbeheer.models import Categorie

class WeezDeelnemerTypeMapper(Mapper[dict, None, Categorie]):
    """Categorie uit het `category`-blok van een evenement.

    alt_naam wordt enkel bij het aanmaken gezet, zodat een aangepaste
    alternatieve naam niet elke run overschreven raakt.
    """

    def map(self, bron: dict, context: None = None) -> Doelgegevens[Categorie]:
        naam = bron.get("naam", "")
        return Doelgegevens(
            sleutels={"id": str(bron["id"])},
            velden={"naam": naam},
        )
