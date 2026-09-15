"""Module die een klasse IntegreatProvider aanbiedt voor het aangeven van de ID kolom
"""
from inschrijfbeheer.mapping.providers.data_provider import DatabaseDataProvider, IntegreatFilter
from typing import TypeVar

T = TypeVar("T")

class IntegreatProvider(DatabaseDataProvider[T, IntegreatFilter]):
    """Klasse die DatabaseDataProvider implementeert om standaard kolom van het ID aan te duiden
    """

    databank = "integreat"
    identifier_veld = "oid"

    