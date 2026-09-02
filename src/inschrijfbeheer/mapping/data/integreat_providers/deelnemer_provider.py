from inschrijfbeheer.mapping.data.data_provider import DatabaseDataProvider
from inschrijfbeheer.models import IntegreatParticipant

class EvenementDatabaseProvider(DatabaseDataProvider[IntegreatParticipant]):
    model = IntegreatParticipant
    identifier_veld= "lid_id"
    