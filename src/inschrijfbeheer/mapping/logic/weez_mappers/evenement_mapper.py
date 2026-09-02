from inschrijfbeheer.mapping.logic import Mapper
from inschrijfbeheer.models import Evenement

class WeezEvenementMapper(Mapper[dict, Evenement]):

    def map(self, bron):
        return super().map(bron)

    def map_alle(self, bronnen):
        return super().map_alle(bronnen)