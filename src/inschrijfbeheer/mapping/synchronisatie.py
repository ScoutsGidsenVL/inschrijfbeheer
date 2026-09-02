"""Module die een klasse bevat die als interface kan dienen voor synchronisatie met een databron
"""
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto
import logging

from inschrijfbeheer.models import Evenement, Inschrijving


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


class Synchronisatie:
    """Superklasse voor mappers om een gelijkaardige interface te geven
    """

    logger = logging.getLogger("inschrijfbeheer")

    def __init__(self, sync_config: SynchronisatieConfig | None = None):
        self.info = SynchronisatieInfo()
        if sync_config is None:
            sync_config = SynchronisatieConfig()
        self.config = sync_config

    def synchroniseer(self) -> SynchronisatieInfo:
        raise NotImplementedError("Deze methode dient geïmplementeerd door een subklasse")

    def synchroniseer_evenement(self, evenement_id: str, sync_inschrijvingen: bool = False) -> SynchronisatieInfo:
        raise NotImplementedError("Deze methode dient geïmplementeerd door een subklasse")

    def synchroniseer_inschrijvingen(self, evenement: Evenement | None = None) -> SynchronisatieInfo:
        raise NotImplementedError("Deze methode dient geïmplementeerd door een subklasse")

    def synchroniseer_vragen(self, evenement: Evenement | None = None, inschrijving: Inschrijving | None = None) -> SynchronisatieInfo:
        """Methode die alle vragen synchroniseert.
        Indien gegeven doet het dit enkel voor de vragen van een gegeven evenement of een gegeven inschrijving.

        Args:
            evenement (Evenement | None, optional): evenement waarvoor de vragen moeten gesynchroniseerd worden. Defaults to None.
            inschrijving (Inschrijving | None, optional): inschrijving waarvoor de vragen gesynchroniseerd worden. Defaults to None.

        Returns:
            SynchronisatieInfo: info over de huidige synchronisatie
        """
        raise NotImplementedError("Deze methode dient geïmplementeerd door een subklasse")

    def log_info(self) -> None:
        self.logger.info(msg=self.info.formatteer)