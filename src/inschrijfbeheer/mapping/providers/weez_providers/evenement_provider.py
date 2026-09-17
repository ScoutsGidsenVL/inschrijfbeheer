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
    """Evenementen bij Weez.

    Let op het verschil tussen de twee methodes. haal_alle_op() geeft de
    overzichtsrecords terug, die minder velden bevatten dan een detailrecord.
    haal_op() geeft het volledige detailrecord. Alleen dat laatste is bruikbaar
    voor WeezEvenementMapper, dus loop over het overzicht voor de ids en haal
    per id de details op.
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
    def _loopt_nog(evenement: dict, nu: datetime) -> bool:
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
        return eind_datum >= nu
