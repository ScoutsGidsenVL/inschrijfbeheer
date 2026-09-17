from inschrijfbeheer.models import IntegreatParticipantType

from .integreat_provider import IntegreatProvider


class IntegreatParticipantTypeProvider(IntegreatProvider[IntegreatParticipantType]):
    model = IntegreatParticipantType
    identifier_veld = "oid"
