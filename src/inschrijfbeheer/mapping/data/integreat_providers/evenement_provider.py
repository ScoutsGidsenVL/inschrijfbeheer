from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider, IntegreatFilter
from inschrijfbeheer.models import IntegreatSeminar

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatSeminar]):
    model = IntegreatSeminar
    identifier_veld= "oid"
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatSeminar],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatSeminar]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        return queryset.filter(eindtijd__gte=drempel)