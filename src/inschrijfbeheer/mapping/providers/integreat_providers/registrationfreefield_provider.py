from django.db.models import QuerySet

from inschrijfbeheer.mapping.providers.data_provider import EvenementFilter
from inschrijfbeheer.models import (
    IntegreatRegistrationfreefield,
)

from .integreat_provider import IntegreatProvider


class IntegreatRegistrationfreefieldProvider(IntegreatProvider[IntegreatRegistrationfreefield]):
    model = IntegreatRegistrationfreefield
    identifier_veld = "oid"
    selecteer_relaties = ("registration", "registration__seminar", "field")

    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatRegistrationfreefield],
        filter: EvenementFilter,
    ) -> QuerySet[IntegreatRegistrationfreefield]:
        if filter.sync_alles or filter.evenement_id is None:
            return queryset

        queryset = queryset.filter(registration__seminar__code=filter.evenement_id)
        return queryset
