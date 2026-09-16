import logging
from typing import Any, Iterable
from dataclasses import dataclass
from .weez_client import WeezClient
from inschrijfbeheer.mapping.providers.data_provider import LijstProvider


logger = logging.getLogger("inschrijfbeheer")


@dataclass(frozen=True)
class TariefFilter:
    evenement_id: str


class WeezTariefProvider(LijstProvider[dict, TariefFilter]):
    """Tarieven bij Weez.

    Tarieven worden geen eigen model, ze dienen enkel om de prijs van een
    inschrijving te bepalen. Vandaar een provider zonder bijhorende mapper.
    """

    MODULE = "ticket"
    RESOURCE = "events"
 
    def __init__(self, client: WeezClient):
        self.client = client

    def haal_alle_op(self, filter: TariefFilter | None = None) -> Iterable[dict]:
        if filter is None:
            raise ValueError("TariefFilter met een evenement_id is verplicht")

        respons = self.client.get(
            f"https://api.weezevent.com/ticket/organizations/{self.client.organisatie}/events/{filter.evenement_id}/rates"
        )
        return respons