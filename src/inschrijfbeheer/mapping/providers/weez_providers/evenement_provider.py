from datetime import datetime, timedelta, timezone
import logging
from dataclasses import dataclass
from typing import Iterable
from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import parse_datetime
from inschrijfbeheer.mapping.providers.data_provider import DataProvider
from .weez_client import WeezClient

logger = logging.getLogger("inschrijfbeheer")

@dataclass(frozen=True)
class EvenementFilter:
    alles: bool = False


class WeezEvenementProvider(DataProvider[dict, EvenementFilter]):
    """Evenementen ophalen uit de WeezTicket API

    Maakt gebruik van de WeezClient om API requests te maken en zo alle evenementen of een specifiek evenement op te halen.
    """

    MODULE = "ticket"
    RESOURCE = "events"
 
    def __init__(self, client: WeezClient):
        self.client = client
 
    def haal_op(self, identifier: str) -> dict | None:
        evenement = self.client.get(f"https://api.weezevent.com/ticket/organizations/{self.client.organisatie}/events/{identifier}")
        if evenement is None:
            logger.warning("Geen evenement gevonden bij Weez voor id %s", identifier)
        return evenement
 
    def haal_alle_op(self, filter: EvenementFilter | None = None) -> Iterable[dict]:
        """Haalt alle evenementen op

        Args:
            filter (EvenementFilter | None, optional): filter die kan aangeven of alle evenementen moeten worden opgehaald. Defaults to None.

        Returns:
            Iterable[dict]: lijst van evenementen zoals teruggegeven door de API en gefilterd
        """
        if filter is None:
            filter = EvenementFilter()

        respons = self.client.get(
            f"https://api.weezevent.com/ticket/organizations/{self.client.organisatie}/events",
            params={"time_status": "terminated"}
        )

        if filter.alles:
            return respons

        nu = datetime.now(timezone(timedelta(hours=1)))
        actueel = [evenement for evenement in respons if self._loopt_nog(evenement, nu)]
        return actueel

    @staticmethod
    def _loopt_nog(evenement: dict, tijdstip: datetime) -> bool:
        """Kijkt of een evenement nog moet komen of bezig is om te filteren indien nodig
        Gebruikt standaard de einddatum, indien niet gegeven gebruikt het daarvoor de startdatum

        Args:
            evenement (dict): een evenement zoals voorgesteld door de API
            tijdstip (datetime): tijdstip waar het evenement na moet liggen

        Returns:
            bool: _description_
        """
        einde = evenement.get("end_date")
        if not einde:
            einde = evenement.get("start_date")

        try:
            eind_datum = parse_datetime(einde)
        except ValueError:
            logger.warning(
                "Onleesbare einddatum %r bij evenement %s, we houden het in de lijst",
                einde,
                evenement.get("id"),
            )
            return True

        if eind_datum.tzinfo is None:
            eind_datum = eind_datum.replace(tzinfo=timezone(timedelta(hours=1)))
        return eind_datum >= tijdstip
