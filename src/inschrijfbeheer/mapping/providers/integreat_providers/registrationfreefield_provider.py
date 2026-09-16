
from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.providers.data_provider import EvenementFilter
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
        filter: EvenementFilter,
    ) -> QuerySet[IntegreatRegistrationfreefield]:
        if filter.sync_alles or filter.evenement_id is None:
            return queryset
 
        queryset = queryset.filter(registration__seminar__code=filter.evenement_id)
        return queryset