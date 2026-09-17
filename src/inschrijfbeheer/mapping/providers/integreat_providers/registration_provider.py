from django.db.models import QuerySet

from inschrijfbeheer.mapping.providers.data_provider import EvenementFilter
from inschrijfbeheer.models import IntegreatRegistration

from .integreat_provider import IntegreatProvider


class IntegreatRegistrationProvider(IntegreatProvider[IntegreatRegistration]):
    model = IntegreatRegistration
    identifier_veld = "oid"

    selecteer_relaties = ("seminar",)

    def pas_filter_toe(
        self,
        queryset: QuerySet[IntegreatRegistration],
        filter: EvenementFilter,
    ) -> QuerySet[IntegreatRegistration]:
        if filter.sync_alles or filter.evenement_id is None:
            return queryset

        queryset = queryset.filter(seminar__code=filter.evenement_id)
        return queryset
