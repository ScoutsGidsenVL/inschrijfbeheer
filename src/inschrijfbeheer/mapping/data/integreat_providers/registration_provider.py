from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider, IntegreatFilter
from inschrijfbeheer.models import IntegreatRegistration

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatRegistration]):
    model = IntegreatRegistration
    identifier_veld= "oid"

    def basis_queryset(self) -> QuerySet[IntegreatRegistration]:
        return self.model.objects.select_related("seminar")
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatRegistration],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatRegistration]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        return queryset.filter(seminar__eindtijd__gte=drempel)