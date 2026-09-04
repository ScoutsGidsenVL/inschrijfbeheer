from django.utils import timezone

from inschrijfbeheer.models import (
    Categorie,
    Evenement,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .weez_mappers import parse_datetime

class WeezEvenementMapper(Mapper[dict, Categorie | None, Evenement]):
    """Evenement uit een detailrecord. De context is de al bewaarde categorie.

    De aantallen en de minimumleeftijd komen niet uit Weez en worden daarom
    enkel bij het aanmaken op nul gezet. Anders wist elke synchronisatie wat
    iemand handmatig invulde.
    """

    def map(self, bron: dict, context: Categorie | None) -> Doelgegevens[Evenement]:
        if bron.get("id") is None:
            raise MappingFout("evenement zonder id")

        periode = bron.get("period") or {}
        start = parse_datetime(periode.get("start"))
        if start is None:
            raise MappingFout(f"evenement {bron['id']} heeft geen bruikbare starttijd")
        einde = parse_datetime(periode.get("end")) or start

        locatie = bron.get("venue") or {}
        return Doelgegevens(
            sleutels={"id": str(bron["id"])},
            velden={
                "titel": bron.get("title", ""),
                "beschrijving": bron.get("description", ""),
                "starttijd": start,
                "eindtijd": einde,
                "locatie_naam": locatie.get("name"),
                "locatie_straat": locatie.get("address"),
                "locatie_stad": locatie.get("city"),
                "locatie_postcode": locatie.get("zip_code"),
                "categorie": context,
                "is_weez": True,
                "laatste_sync": timezone.now(), 
            },
        )