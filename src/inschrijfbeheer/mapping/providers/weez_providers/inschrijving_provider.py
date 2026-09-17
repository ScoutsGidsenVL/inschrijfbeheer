import logging
from dataclasses import dataclass
from typing import Iterable

from inschrijfbeheer.mapping.providers.data_provider import LijstProvider

from .weez_client import WeezClient

logger = logging.getLogger("inschrijfbeheer")


@dataclass(frozen=True)
class InschrijvingFilter:
    evenement_id: str
    sinds: str | None = None
    sync_alles: bool = False


class WeezInschrijvingProvider(LijstProvider[dict, InschrijvingFilter]):
    TEST = True
    """Deelnemers bij Weez.

    Weez heeft geen endpoint voor één losse deelnemer, dus deze provider kan
    enkel lijsten leveren, en altijd afgebakend per evenement. Met `sinds`
    haal je enkel op wat sinds dat tijdstip gewijzigd is.
    """

    MODULE = "ticket"
    RESOURCE = "attendees"

    def __init__(self, client: WeezClient):
        self.client = client

    def haal_op(self, identifier: str, evenement_id: str) -> dict | None:
        deelnemer = self.client.get(
            f"https://api.weezevent.com/ticket/organizations/{self.client.organisatie}" f"/events/{evenement_id}/attendees/{identifier}"
        )

        if not deelnemer:
            logger.warning("Geen deelnemer gevonden bij Weez voor id %s in evenement %s", identifier, evenement_id)
            return None
        return deelnemer

    def haal_alle_op(self, filter: InschrijvingFilter | None = None) -> Iterable[dict]:
        if filter is None:
            raise ValueError("InschrijvingFilter met een evenement_id is verplicht")

        parameters = {"include_deleted": "true"}
        if not filter.sync_alles and filter.sinds:
            parameters["modified__gt"] = filter.sinds

        respons = self.client.get(
            f"https://api.weezevent.com/ticket/organizations/{self.client.organisatie}" f"/events/{filter.evenement_id}/attendees",
            params=parameters,
        )
        if self.TEST:
            self.TEST = False
        logger.debug("%s deelnemers opgehaald bij Weez voor evenement %s", len(respons), filter.evenement_id)
        return respons
