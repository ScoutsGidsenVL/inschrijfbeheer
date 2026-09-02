from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider
from inschrijfbeheer.models import IntegreatSeminarType
from .integreat_provider import IntegreatProvider

class IntegreatSeminarTypeProvider(IntegreatProvider[IntegreatSeminarType]):
    model = IntegreatSeminarType
    identifier_veld= "code"