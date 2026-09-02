from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider
from inschrijfbeheer.models import IntegreatParticipantType

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatParticipantType]):
    model = IntegreatParticipantType
    identifier_veld= "oid"