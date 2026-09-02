from django.db.models import QuerySet

from .integreat_provider import IntegreatProvider
from inschrijfbeheer.models import IntegreatSeminarType

class IntegreatSeminarTypeProvider(IntegreatProvider[IntegreatSeminarType]):
    model = IntegreatSeminarType
    identifier_veld= "code" # id van Categorie is gelijk aan 'code'

    def basis_queryset(self) -> QuerySet[IntegreatSeminarType]:
        return self.model.objects.all()