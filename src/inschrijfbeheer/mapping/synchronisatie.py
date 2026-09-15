"""Module die een klasse bevat die als interface kan dienen voor synchronisatie met een databron
"""
from abc import ABC, abstractmethod
import logging
from typing import Callable, ClassVar, TypeVar

from django.db import transaction

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

    Een subklasse bouwt haar providers en onderdelen zelf op, zodat je ze met
    niets meer dan een SynchronisatieConfig aanmaakt:

        WeezSyncer(SynchronisatieConfig(limiet=5, dry_run=True)).voer_uit()
    """

    logger = logging.getLogger("inschrijfbeheer")

    #: naam op de commandoregel, ook het voorvoegsel in de logs
    naam: ClassVar[str] = ""

    #: configvelden die alleen deze bron gebruikt, voor de waarschuwing in het commando
    eigen_opties: ClassVar[frozenset[str]] = frozenset()

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

    def voer_uit(self, actie: Callable[[], SynchronisatieInfo] | None = None) -> SynchronisatieInfo:
        """Draait een synchronisatie in een eigen transactie en logt het resultaat.

        Zonder argument draait ze volledig. Geef een actie mee voor een deel,
        bijvoorbeeld de inschrijvingen van één evenement:

            syncer.voer_uit(partial(syncer.synchroniseer_inschrijvingen, evenement))

        Elke bron krijgt een eigen transactie, zodat een fout in de ene bron de
        andere niet raakt. Bij een dry-run draait alles terug na afloop.

        Args:
            actie (Callable[[], SynchronisatieInfo] | None, optional): wat er binnen
                de transactie draait. Defaults to None, dan synchroniseer().

        Returns:
            SynchronisatieInfo: info over de huidige synchronisatie
        """
        if actie is None:
            actie = self.synchroniseer

        with transaction.atomic():
            info = actie()
            self.log_info()

            if self.config.dry_run:
                transaction.set_rollback(True)
                self.logger.info(
                    "%s Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen.",
                    self.aanduiding,
                )

        return info

    @property
    def aanduiding(self) -> str:
        """Voorvoegsel voor de logregels van deze bron, bijvoorbeeld [WEEZ SYNC]."""
        return f"[{(self.naam or type(self).__name__).upper()} SYNC]"

    def bewaar(self, onderdelen: SyncOnderdelen[N], doel: Doelgegevens[N]) -> tuple[N, bool]:
        return self.databank.bewaar(onderdelen, doel)

    def log_info(self) -> None:
        self.logger.info(msg=self.info.formatteer())