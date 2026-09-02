from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider
from inschrijfbeheer.models import IntegreatSeminarFreeFieldType

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatSeminarFreeFieldType]):
    model = IntegreatSeminarFreeFieldType
    identifier_veld= "code"