"""Module die een klasse bevat die als interface kan dienen voor synchronisatie met een databron
"""
from abc import ABC, abstractmethod
import logging
from typing import TypeVar

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens
from inschrijfbeheer.mapping.utils import (
    SynchronisatieConfig,
    SynchronisatieInfo,
    SyncOnderdelen,
    InschrijfbeheerDatabank
)

N = TypeVar('N')

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
        self.databank = InschrijfbeheerDatabank(info=self.info)
 
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
        return self.databank.bewaar(onderdelen, doel)
 
    def log_info(self) -> None:
        self.logger.info(msg=self.info.formatteer())