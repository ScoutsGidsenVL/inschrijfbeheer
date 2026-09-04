from inschrijfbeheer.models import (
    Categorie,
)

from inschrijfbeheer.mapping.logic.mapper import (
    Doelgegevens,
    Mapper,
    MappingFout,
)



class WeezCategorieMapper(Mapper[dict, None, Categorie]):
    """Categorie uit het `category`-blok van een evenement.

    alt_naam wordt enkel bij het aanmaken gezet, zodat een aangepaste
    alternatieve naam niet elke run overschreven raakt.
    """

    def map(self, bron: dict, context: None = None) -> Doelgegevens[Categorie]:
        if bron.get("id") is None:
            raise MappingFout("categorie zonder id")

        naam = bron.get("name", "")
        return Doelgegevens(
            sleutels={"id": str(bron["id"])},
            velden={"naam": naam, "alt_naam": naam, "is_weez": True},
        )

