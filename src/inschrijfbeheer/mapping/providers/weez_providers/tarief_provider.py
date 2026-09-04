import logging
from typing import Any, Iterable
from dataclasses import dataclass
from .weez_provider import WeezClient
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

    def __init__(self, client: WeezClient):
        self.client = client

    def haal_alle_op(self, filter: TariefFilter | None = None) -> Iterable[dict]:
        if filter is None:
            raise ValueError("TariefFilter met een evenement_id is verplicht")

        respons = self.client.get("tickets", parameters={"id_event[]": filter.evenement_id})
        evenementen = respons.get("events") or []
        if not evenementen:
            logger.warning("Geen tarieven gevonden voor evenement %s", filter.evenement_id)
            return []
        return evenementen[0].get("tickets") or []

    def haal_tarieven_op(self, evenement_id: str) -> dict[str, str]:
        """Geeft de tarieven van een evenement als {id: id, prijs: prijs, naam: naam}."""
        return [
            {"id": tarief.get("id"), "prijs": tarief.get("price"), "naam": tarief.get("name")}
            for tarief in self.haal_alle_op(TariefFilter(evenement_id=evenement_id))
        ]