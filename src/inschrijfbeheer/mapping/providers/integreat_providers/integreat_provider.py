from inschrijfbeheer.mapping.providers.data_provider import DatabaseDataProvider, IntegreatFilter
from typing import TypeVar

T = TypeVar("T")

class IntegreatProvider(DatabaseDataProvider[T, IntegreatFilter]):

    databank = "integreat"
    identifier_veld = "oid"

    def pas_filter_toe(self, queryset, filter: IntegreatFilter):
        if filter.limiet is not None:
            return queryset[:filter.limiet]
        return queryset

    