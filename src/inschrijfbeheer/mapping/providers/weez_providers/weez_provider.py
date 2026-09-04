"""Providers voor de Weezevent-API."""

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from inschrijfbeheer.utils.weez_api import doe_weez_get, maak_sessie

from inschrijfbeheer.mapping.providers.data_provider import DataProvider, LijstProvider

logger = logging.getLogger("inschrijfbeheer")


class WeezClient:
    """Houdt de HTTP-sessie naar Weez vast en voert de GET-aanroepen uit.

    Alle Weez-providers krijgen dezelfde client mee, zodat ze samen één sessie
    delen. Synchronisatie opent en sluit hem:

        with WeezClient() as client:
            provider = WeezEvenementProvider(client)
            ...

    De sessie ontstaat pas bij het openen, zodat je de providers al kan
    samenstellen voordat de synchronisatie begint.
    """

    def __init__(self):
        self._sessie = None

    def __enter__(self) -> "WeezClient":
        self._sessie = maak_sessie()
        return self

    def __exit__(self, *_) -> None:
        if self._sessie is not None:
            self._sessie.close()
            self._sessie = None

    def get(self, pad: str, parameters: dict | None = None) -> dict:
        if self._sessie is None:
            raise RuntimeError("WeezClient is niet geopend, gebruik hem als context manager")
        if parameters is None:
            return doe_weez_get(self._sessie, pad)
        return doe_weez_get(self._sessie, pad, parameters=parameters)


@dataclass(frozen=True)
class EvenementFilter:
    include_without_sales: bool = True


class WeezEvenementProvider(DataProvider[dict, EvenementFilter]):
    """Evenementen bij Weez.

    Let op het verschil tussen de twee methodes. haal_alle_op() geeft de
    overzichtsrecords terug, die minder velden bevatten dan een detailrecord.
    haal_op() geeft het volledige detailrecord. Alleen dat laatste is bruikbaar
    voor WeezEvenementMapper, dus loop over het overzicht voor de ids en haal
    per id de details op.
    """

    def __init__(self, client: WeezClient):
        self.client = client

    def haal_op(self, identifier: str) -> dict | None:
        respons = self.client.get(f"event/{identifier}/details")
        return respons.get("events") or None

    def haal_alle_op(self, filter: EvenementFilter | None = None) -> Iterable[dict]:
        if filter is None:
            filter = EvenementFilter()
        respons = self.client.get(
            "events",
            parameters={"include_without_sales": "1" if filter.include_without_sales else "0"},
        )
        return respons.get("events") or []


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

        parameters = {"id_event[]": filter.evenement_id, "full": "1", "include_deleted": "1"}
        if filter.sinds:
            parameters["last_update"] = filter.sinds

        respons = self.client.get("participant/list", parameters=parameters)
        return respons.get("participants") or []


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

    def haal_tarieven_op(self, evenement_id: str) -> dict[str, Any]:
        """Geeft de tarieven van een evenement als {tarief_id: prijs}."""
        return {
            tarief.get("id"): tarief.get("price")
            for tarief in self.haal_alle_op(TariefFilter(evenement_id=evenement_id))
        }
