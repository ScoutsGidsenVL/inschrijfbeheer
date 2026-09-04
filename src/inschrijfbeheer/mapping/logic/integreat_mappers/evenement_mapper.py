from dataclasses import dataclass

from django.utils import timezone

from inschrijfbeheer.models import (
    Categorie,
    Evenement,
    EvenementStatus,
    IntegreatSeminar,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout
from .integreat_mapper import normaliseer_code, tekst

@dataclass(frozen=True)
class EvenementContext:
    """De status en de categorie zijn al bewaard voor het evenement gemapt wordt."""

    status: EvenementStatus
    categorie: Categorie


class IntegreatEvenementMapper(Mapper[IntegreatSeminar, EvenementContext, Evenement]):
    """Evenement uit een seminar.
    """

    def map(self, bron: IntegreatSeminar, context: EvenementContext) -> Doelgegevens[Evenement]:
        code = normaliseer_code(bron.code)
        if not code:
            raise MappingFout(f"seminar {bron.oid} zonder code")

        if bron.locatie_stad:
            locatie_stad = tekst(bron.locatie_stad.naam)
            locatie_postcode = tekst(bron.locatie_stad.postcode)
        else:
            locatie_stad, locatie_postcode = None, None

        return Doelgegevens(
            sleutels={"id": code},
            velden={
                "titel": tekst(bron.naam),
                "beschrijving": tekst(bron.onderwerp),
                "status": context.status,
                "categorie": context.categorie,
                "locatie_naam": bron.locatie_naam,
                "locatie_straat": bron.locatie_straat,
                "locatie_stad": locatie_stad,
                "locatie_postcode": locatie_postcode,
                "starttijd": bron.starttijd,
                "eindtijd": bron.eindtijd,
                "laatste_sync": timezone.now(), 
            }
        )
