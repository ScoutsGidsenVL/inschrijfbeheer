from typing import TypeVar

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens
from .synchronisatie import SyncOnderdelen, SynchronisatieActie, SynchronisatieInfo

N = TypeVar('N')

class InschrijfbeheerDatabank:

    def __init__(self, info: SynchronisatieInfo):
        self.info = info

    def bewaar(self, onderdelen: SyncOnderdelen[N], doel: Doelgegevens[N]) -> tuple[N, bool]:
        """Bewaart Doelgegevens en registreert de actie.
 
        Dit is de enige plek waar de synchronisatie naar de databank schrijft,
        zodat het tellen niet per model apart gebeurt en niet kan afwijken van
        wat er echt gebeurd is.
 
        Returns:
            tuple[N, bool]: het bewaarde object en of het aangemaakt werd
        """
        manager = onderdelen.model.objects
        pk_naam = onderdelen.model._meta.pk.name

        if doel.vervang_bestaande:
            filter_sleutels = doel.vervang_sleutels or doel.sleutels
            verouderd = manager.filter(**filter_sleutels)

            nieuwe_pk = doel.velden.get(pk_naam, doel.sleutels.get(pk_naam))
            if nieuwe_pk is not None:
                verouderd = verouderd.exclude(pk=nieuwe_pk)

            for bestaand in verouderd:
                bestaand.delete()
                self.info.registreer(onderdelen.model, SynchronisatieActie.VERWIJDERD)
 
        if onderdelen.enkel_aanmaken:
            bewaard, aangemaakt = manager.get_or_create(
                **doel.sleutels,
                defaults={**doel.velden},
            )

            if aangemaakt:
                self.info.registreer(onderdelen.model, SynchronisatieActie.AANGEMAAKT)
            return bewaard, aangemaakt

        bewaard, aangemaakt = manager.update_or_create(**doel.sleutels, defaults=doel.velden)
 
        self.info.registreer(
            onderdelen.model,
            SynchronisatieActie.AANGEMAAKT if aangemaakt else SynchronisatieActie.BIJGEWERKT,
        )
        return bewaard, aangemaakt