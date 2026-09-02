from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider
from inschrijfbeheer.models import IntegreatSeminarStatus

class IntegreatSeminarStatusProvider(DatabaseDataProvider[IntegreatSeminarStatus]):
    model = IntegreatSeminarStatus
    identifier_veld= "beschrijving"