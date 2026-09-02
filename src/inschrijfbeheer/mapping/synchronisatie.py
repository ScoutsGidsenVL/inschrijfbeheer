"""Module die een klasse bevat die als interface kan dienen voor synchronisatie met een databron
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto
import logging

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper
from inschrijfbeheer.mapping.data.data_provider import LijstProvider, ObjectProvider


class SynchronisatieActie(Enum):
    AANGEMAAKT = auto()
    BIJGEWERKT = auto()
    OVERGESLAGEN = auto()


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



N = TypeVar("N")


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
 
 
class Synchronisatie(ABC):
    """Superklasse voor synchronisaties, geeft elke bron dezelfde interface.
 
    Deze klasse haalt zelf niets op en mapt zelf niets. Dat doen de providers
    en mappers die een subklasse via SyncOnderdelen bijhoudt. Synchronisatie
    bepaalt de volgorde, stelt de context samen, bewaart via bewaar() en houdt
    de voortgang bij in self.info.
    """
 
    logger = logging.getLogger("inschrijfbeheer")
 
    def __init__(self, sync_config: SynchronisatieConfig | None = None):
        self.info = SynchronisatieInfo()
        if sync_config is None:
            sync_config = SynchronisatieConfig()
        self.config = sync_config
 
    @abstractmethod
    def synchroniseer(self) -> SynchronisatieInfo:
        """Voert een volledige synchronisatie uit.
 
        Hier hoort de volgorde vastgelegd te worden. Een evenement moet lokaal
        bestaan voor je er inschrijvingen aan kan koppelen, en een vraag voor
        je er een antwoord aan kan koppelen.
        """
        raise NotImplementedError("Deze methode dient geimplementeerd door een subklasse")
 
    @abstractmethod
    def synchroniseer_evenement(self, evenement_id: str, sync_inschrijvingen: bool = False) -> SynchronisatieInfo:
        raise NotImplementedError("Deze methode dient geimplementeerd door een subklasse")
 
    @abstractmethod
    def synchroniseer_inschrijvingen(self, evenement=None) -> SynchronisatieInfo:
        raise NotImplementedError("Deze methode dient geimplementeerd door een subklasse")
 
    @abstractmethod
    def synchroniseer_vragen(self, evenement=None, inschrijving=None) -> SynchronisatieInfo:
        """Methode die alle vragen synchroniseert.
        Indien gegeven doet het dit enkel voor de vragen van een gegeven evenement of een gegeven inschrijving.
 
        Args:
            evenement (Evenement | None, optional): evenement waarvoor de vragen moeten gesynchroniseerd worden. Defaults to None.
            inschrijving (Inschrijving | None, optional): inschrijving waarvoor de vragen gesynchroniseerd worden. Defaults to None.
 
        Returns:
            SynchronisatieInfo: info over de huidige synchronisatie
        """
        raise NotImplementedError("Deze methode dient geimplementeerd door een subklasse")
 
    def bewaar(self, onderdelen: SyncOnderdelen[N], doel: Doelgegevens[N]) -> tuple[N, bool]:
        """Bewaart Doelgegevens en registreert de actie.
 
        Dit is de enige plek waar de synchronisatie naar de databank schrijft,
        zodat het tellen niet per model apart gebeurt en niet kan afwijken van
        wat er echt gebeurd is.
 
        Returns:
            tuple[N, bool]: het bewaarde object en of het aangemaakt werd
        """
        manager = onderdelen.model.objects
 
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
 
    def log_info(self) -> None:
        self.logger.info(msg=self.info.formatteer())