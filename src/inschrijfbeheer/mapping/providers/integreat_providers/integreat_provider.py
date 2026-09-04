"""Module die een klasse IntegreatProvider aanbiedt voor het toepassen van de limiet op querysets
"""
from inschrijfbeheer.mapping.providers.data_provider import DatabaseDataProvider, IntegreatFilter
from typing import TypeVar

T = TypeVar("T")

class IntegreatProvider(DatabaseDataProvider[T, IntegreatFilter]):
    """Klasse die DatabaseDataProvider implementeert om de limiet toe te passen op de Integreat databank
    """

    databank = "integreat"
    identifier_veld = "oid"

    def pas_filter_toe(self, queryset, filter: IntegreatFilter):
        """Past limiet toe op de queryset zodat maximaal LIMIET elementen worden opgehaald
        """
        if filter.limiet is not None:
            return queryset[:filter.limiet]
        return queryset

    