from inschrijfbeheer.mapping.data import ApiDataProvider


class WeezEvenementProvider(ApiDataProvider):

    def haal_op(self, identifier):
        return super().haal_op(identifier)

    def haal_alle_op(self):
        return super().haal_alle_op()