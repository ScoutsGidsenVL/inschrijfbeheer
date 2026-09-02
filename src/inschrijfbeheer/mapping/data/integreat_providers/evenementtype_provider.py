from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider
from inschrijfbeheer.models import IntegreatSeminarType

class IntegreatSeminarTypeProvider(DatabaseDataProvider[IntegreatSeminarType]):
    model = IntegreatSeminarType
    identifier_veld= "code"