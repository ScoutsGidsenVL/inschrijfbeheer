"""Provider voor de ledenopzoeking via SOAP."""

import logging
from typing import Any

from inschrijfbeheer.utils.soap import haal_lidgegevens

from .data_provider import ObjectProvider

logger = logging.getLogger("inschrijfbeheer")


class LidProvider(ObjectProvider[Any]):
    """Zoekt één lid op via zijn lidnummer.

    Deze bron heeft geen lijstvariant, vandaar enkel ObjectProvider. Vervang
    Any door het type dat haal_lidgegevens teruggeeft zodra dat een eigen
    klasse heeft.
    """

    def haal_op(self, identifier: str) -> Any | None:
        try:
            return haal_lidgegevens(identifier)
        except Exception as fout:
            # De SOAP-laag gooit uiteenlopende fouten, van netwerkproblemen
            # tot een onbekend lidnummer. Voor de synchronisatie is dat
            # allemaal hetzelfde: geen lid gevonden.
            logger.warning("Ledenopzoeking mislukt voor %s: %s", identifier, fout)
            return None