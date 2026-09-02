
from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider, IntegreatFilter
from inschrijfbeheer.models import (
    IntegreatRegistrationfreefield,
)

class IntegreatRegistrationfreefieldProvider(DatabaseDataProvider[IntegreatRegistrationfreefield]):
    model = IntegreatRegistrationfreefield
    identifier_veld= "oid"

    def basis_queryset(self) -> QuerySet[IntegreatRegistrationfreefield]:
        return self.model.objects.select_related("registration", "registration__seminar", "field")
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatRegistrationfreefield],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatRegistrationfreefield]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        return queryset.filter(registration__seminar__eindtijd__gte=drempel)