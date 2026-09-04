import logging
from dataclasses import dataclass
from typing import Iterable
from .weez_provider import WeezClient
from inschrijfbeheer.mapping.providers.data_provider import LijstProvider


logger = logging.getLogger("inschrijfbeheer")


@dataclass(frozen=True)
class InschrijvingFilter:
    evenement_id: str
    sinds: str | None = None


class WeezInschrijvingProvider(LijstProvider[dict, InschrijvingFilter]):
    """Deelnemers bij Weez.

    Weez heeft geen endpoint voor één losse deelnemer, dus deze provider kan
    enkel lijsten leveren, en altijd afgebakend per evenement. Met `sinds`
    haal je enkel op wat sinds dat tijdstip gewijzigd is.
    """

    def __init__(self, client: WeezClient):
        self.client = client

    def haal_alle_op(self, filter: InschrijvingFilter | None = None) -> Iterable[dict]:
        if filter is None:
            raise ValueError("InschrijvingFilter met een evenement_id is verplicht")

        parameters = {"id_event[]": filter.evenement_id, "full": "1"}
        if filter.sinds:
            parameters["last_update"] = filter.sinds

        respons = self.client.get("participant/list", parameters=parameters)
        return respons.get("participants") or []
