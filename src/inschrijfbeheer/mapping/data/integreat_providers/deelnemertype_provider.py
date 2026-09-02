from .integreat_provider import IntegreatProvider
from inschrijfbeheer.models import IntegreatParticipantType

class IntegreatParticipantTypeProvider(IntegreatProvider[IntegreatParticipantType]):
    model = IntegreatParticipantType
    identifier_veld= "oid"