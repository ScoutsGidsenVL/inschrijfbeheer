from django.db.models import QuerySet

from inschrijfbeheer.mapping.providers.data_provider import EvenementFilter
from inschrijfbeheer.models import IntegreatSeminarFreeField

from .integreat_provider import IntegreatProvider


class IntegreatSeminarFreeFieldProvider(IntegreatProvider[IntegreatSeminarFreeField]):
    model = IntegreatSeminarFreeField
    identifier_veld = "oid"
    selecteer_relaties = ("seminar",)

    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatSeminarFreeField],
        filter: EvenementFilter,
    ) -> QuerySet[IntegreatSeminarFreeField]:
        if filter.sync_alles or filter.evenement_id is None:
            return queryset

        queryset = queryset.filter(seminar__code=filter.evenement_id)
        return queryset
