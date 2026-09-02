from abc import ABC, abstractmethod
from typing import Generic, Iterable, TypeVar

from django.db.models import Model
from django.db.models.query import QuerySet

T = TypeVar("T")
M = TypeVar("M", bound=Model)


class DataProvider(Generic[T], ABC):
    """Basiscontract voor het ophalen van één soort object bij een bron.

    Elke combinatie van bron en objecttype (WeezEvent-evenementen,
    WeezEvent-inschrijvingen, evenementen uit de eigen databank, ...) krijgt
    zijn eigen concrete DataProvider, maar ze delen allemaal dit contract:
    één object opvragen via een identifier, of alles opvragen.
    """

    @abstractmethod
    def haal_op(self, identifier: str) -> T | None:
        """Haalt één object op via zijn identifier bij de bron.

        Geeft None terug als er bij de bron niets met die identifier bestaat.
        """
        raise NotImplementedError

    @abstractmethod
    def haal_alle_op(self) -> Iterable[T]:
        """Haalt alle objecten van dit type op bij de bron.

        Dit kan een gewone lijst zijn (bv. bij een JSON-API), maar evengoed
        een QuerySet of BaseManager (bij een databankbron). Beide zijn
        Iterable[T], dus de aanroeper hoeft het onderscheid niet te kennen.
        """
        raise NotImplementedError


class ApiDataProvider(DataProvider[dict], ABC):
    """Basisklasse voor providers die via een JSON-API werken.
    """


class DatabaseDataProvider(DataProvider[M], ABC):
    """Basisklasse voor providers die hun data uit de eigen databank halen.
    """

    identifier_veld: str = "oid"

    @property
    @abstractmethod
    def model(self) -> type[M]:
        """Het model waarvan deze provider objecten ophaalt.
        """
        raise NotImplementedError

    def haal_op(self, identifier: str) -> M | None:
        return self.model.objects.filter(**{self.identifier_veld: identifier}).first()

    def haal_alle_op(self) -> QuerySet[M]:
        return self.model.objects.all()