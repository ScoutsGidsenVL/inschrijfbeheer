
from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.providers.data_provider import IntegreatFilter
from .integreat_provider import IntegreatProvider
from inschrijfbeheer.models import (
    IntegreatRegistrationfreefield,
)

class IntegreatRegistrationfreefieldProvider(IntegreatProvider[IntegreatRegistrationfreefield]):
    model = IntegreatRegistrationfreefield
    identifier_veld= "oid"
    selecteer_relaties = ("registration", "registration__seminar", "field")
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatRegistrationfreefield],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatRegistrationfreefield]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        queryset = queryset.filter(registration__seminar__eindtijd__gte=drempel)
        return super().pas_filter_toe(queryset=queryset, filter=filter)