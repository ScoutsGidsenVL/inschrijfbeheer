"""PostgreSQL-backend die PostgreSQL 13 toelaat.

Django 5.2 vereist officieel PostgreSQL 14. Onze server draait nog 13, die end-of-life is.
De enige PG14-functies in de backend (BitXor, covering SP-GiST-indexen) gebruiken we niet.
Verwijder deze backend zodra de databank op 14+ draait.
"""

from django.db.backends.postgresql import base, features


class DatabaseFeatures(features.DatabaseFeatures):
    minimum_database_version = (13,)


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
