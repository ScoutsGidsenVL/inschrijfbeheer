from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from .integreat_provider import IntegreatProvider
from inschrijfbeheer.mapping.providers.data_provider import IntegreatFilter
from inschrijfbeheer.models import IntegreatSeminarFreeField

class IntegreatSeminarFreeFieldProvider(IntegreatProvider[IntegreatSeminarFreeField]):
    model = IntegreatSeminarFreeField
    identifier_veld= "oid"
    selecteer_relaties = ("seminar",)
 
    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatSeminarFreeField],
        filter: IntegreatFilter,
    ) -> QuerySet[IntegreatSeminarFreeField]:
        if filter.sync_alles:
            return queryset
 
        drempel = timezone.now() - timedelta(days=filter.terugblik_dagen)
        queryset = queryset.filter(seminar__eindtijd__gte=drempel)
        return super().pas_filter_toe(queryset=queryset, filter=filter)