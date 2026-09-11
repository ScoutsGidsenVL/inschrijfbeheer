from enum import Enum, auto
from typing import TypeVar, Any, Generic
from dataclasses import dataclass, field
from collections import defaultdict

from inschrijfbeheer.mapping.logic.mapper import Mapper
from inschrijfbeheer.mapping.providers.data_provider import LijstProvider, ObjectProvider


N = TypeVar('N')


class SynchronisatieActie(Enum):
    AANGEMAAKT = auto()
    BIJGEWERKT = auto()
    OVERGESLAGEN = auto()
    VERWIJDERD = auto()


@dataclass
class ModelResultaat:
    """Houdt de tellers van één model bij binnen een synchronisatie."""
    aangemaakt: int = 0
    bijgewerkt: int = 0
    overgeslagen: int = 0

    def registreer(self, actie: SynchronisatieActie) -> None:
        match actie:
            case SynchronisatieActie.AANGEMAAKT:
                self.aangemaakt += 1
            case SynchronisatieActie.BIJGEWERKT:
                self.bijgewerkt += 1
            case SynchronisatieActie.OVERGESLAGEN:
                self.overgeslagen += 1

class SynchronisatieStatus(Enum):
    GESLAAGD = auto()
    FOUTIEF = auto()
    BEZIG = auto()
    WACHTEND = auto()


@dataclass
class SynchronisatieInfo:
    """Klasse die de resultaten van een synchronisatie bijhoudt."""
    _status: SynchronisatieStatus = SynchronisatieStatus.WACHTEND
    resultaten: dict[type, ModelResultaat] = field(
        default_factory=lambda: defaultdict(ModelResultaat)
    )

    def registreer(self, model: type, actie: SynchronisatieActie) -> None:
        self.resultaten[model].registreer(actie)

    def status(self, status: SynchronisatieStatus):
        self._status = status

    def formatteer(self) -> str:
        weergave = f"Status van de synchronisatie {str(self._status)}:\n"
        for model, resultaat in self.resultaten.items():
            weergave += (
                f"{model.__name__} model maakte {resultaat.aangemaakt} nieuwe objecten aan, "
                f"werkte {resultaat.bijgewerkt} objecten bij en sloeg {resultaat.overgeslagen} objecten over\n"
            )
        return weergave


@dataclass
class SynchronisatieConfig:
    limiet: int | None = None
    sync_alles: bool = False





@dataclass
class SyncOnderdelen(Generic[N]):
    """Bundelt wat nodig is om één modeltype te synchroniseren.
 
    Attributes:
        model: het Django-model, nodig om te bewaren en om de actie in
            SynchronisatieInfo te registreren
        mapper: zet brondata plus context om naar Doelgegevens
        provider: haalt de brondata op. Blijft None voor modellen waarvan de
            data genest in het antwoord van een ander model zit, zoals de
            categorie in een evenement of de vragen in een inschrijving.
        enkel_aanmaken: True voor modellen die de synchronisatie na het
            aanmaken niet meer mag overschrijven. Dan gebruikt bewaar()
            get_or_create in plaats van update_or_create.
    """
 
    model: type[N]
    mapper: Mapper[Any, Any, N]
    provider: ObjectProvider | LijstProvider | None = None
    enkel_aanmaken: bool = False