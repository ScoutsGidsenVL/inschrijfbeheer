from inschrijfbeheer.models import (
    Deelnemer,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper
from .weez_mappers import InschrijvingsGegevens, LidResultaat

class WeezDeelnemerMapper(Mapper[InschrijvingsGegevens, LidResultaat, Deelnemer]):
    """Deelnemer uit de ingevulde ledengegevens plus de opzoeking.

    Leverde de opzoeking niets op, dan wordt er een deelnemer bewaard op naam
    en mailadres, met een foutboodschap. Zo gaat de inschrijving niet verloren
    en kan iemand ze achteraf rechtzetten.
    """

    def map(self, bron: InschrijvingsGegevens, context: LidResultaat) -> Doelgegevens[Deelnemer]:
        if context.lidgegevens is None:
            return Doelgegevens(
                sleutels={
                    "voornaam": bron.voornaam,
                    "achternaam": bron.achternaam,
                    "mailadres": bron.mailadres,
                },
                velden={"foutboodschap": context.foutboodschap},
            )

        lid = context.lidgegevens
        return Doelgegevens(
            sleutels={"id": lid.id},
            velden={
                "voornaam": lid.voornaam,
                "achternaam": lid.naam,
                "mailadres": lid.emailadres,
            },
        )


