"""Providers voor de Weezevent-API."""

import logging
from inschrijfbeheer.utils.weez_api import doe_weez_get, maak_sessie

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

