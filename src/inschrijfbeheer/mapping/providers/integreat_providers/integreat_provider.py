"""Module die een klasse IntegreatProvider aanbiedt voor het aangeven van de ID kolom"""

from typing import TypeVar

from inschrijfbeheer.mapping.providers.data_provider import DatabaseDataProvider, IntegreatFilter

T = TypeVar("T")


class IntegreatProvider(DatabaseDataProvider[T, IntegreatFilter]):
    """Klasse die DatabaseDataProvider implementeert om standaard kolom van het ID aan te duiden"""

    databank = "integreat"
    identifier_veld = "oid"
