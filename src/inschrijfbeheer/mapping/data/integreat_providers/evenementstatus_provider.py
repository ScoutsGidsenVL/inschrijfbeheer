from inschrijfbeheer.models import IntegreatSeminarStatus
from .integreat_provider import IntegreatProvider

class IntegreatSeminarStatusProvider(IntegreatProvider[IntegreatSeminarStatus]):
    model = IntegreatSeminarStatus
    identifier_veld= "beschrijving"