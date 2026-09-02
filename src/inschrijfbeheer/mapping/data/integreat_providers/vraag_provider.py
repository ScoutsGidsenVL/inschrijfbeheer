from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider, IntegreatFilter
from inschrijfbeheer.models import IntegreatSeminarFreeField

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatSeminarFreeField]):
    model = IntegreatSeminarFreeField
    identifier_veld= "oid"

    def basis_queryset(self) -> QuerySet[IntegreatSeminarFreeField]:
        return self.model.objects.select_related("seminar")
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatSeminarFreeField],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatSeminarFreeField]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        return queryset.filter(seminar__eindtijd__gte=drempel)