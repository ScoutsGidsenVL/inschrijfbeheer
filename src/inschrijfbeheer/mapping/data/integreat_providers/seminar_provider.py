from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from .integreat_provider import IntegreatProvider
from inschrijfbeheer.mapping.data.data_provider import IntegreatFilter
from inschrijfbeheer.models import IntegreatSeminar

class IntegreatSeminarProvider(IntegreatProvider[IntegreatSeminar]):
    model = IntegreatSeminar
    identifier_veld= "code"
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatSeminar],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatSeminar]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        queryset = queryset.filter(eindtijd__gte=drempel)
        return super().pas_filter_toe(queryset=queryset, filter=filter)