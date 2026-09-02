from datetime import timedelta
 
from django.db.models import QuerySet
from django.utils import timezone

from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider, IntegreatFilter
from inschrijfbeheer.models import IntegreatSeminarType

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatSeminarType]):
    model = IntegreatSeminarType
    identifier_veld= "code" # id van Categorie is gelijk aan 'code'

    def basis_queryset(self) -> QuerySet[IntegreatSeminarType]:
        return self.model.objects.all()