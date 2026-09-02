from inschrijfbeheer.models import IntegreatSeminarFreeFieldType
from .integreat_provider import IntegreatProvider

class IntegreatSeminarFreeFieldTypeProvider(IntegreatProvider[IntegreatSeminarFreeFieldType]):
    model = IntegreatSeminarFreeFieldType
    identifier_veld= "code"