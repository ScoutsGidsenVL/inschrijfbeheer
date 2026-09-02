from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, TypeVar

from django.db.models import Model
from django.db.models.query import QuerySet

T = TypeVar("T")
F = TypeVar("F")
M = TypeVar("M", bound=Model)


class ObjectProvider(Generic[T], ABC):
    """Voor bronnen die één object per identifier kunnen leveren."""

    @abstractmethod
    def haal_op(self, identifier: str) -> T | None:
        """Haalt één object op via zijn identifier.

        Geeft None terug als er bij de bron niets met die identifier bestaat.
        """
        raise NotImplementedError


class LijstProvider(Generic[T, F], ABC):
    """Voor bronnen die meerdere objecten kunnen leveren.

    Het filter is een klein dataklasje per provider, zodat de afbakening
    (welk evenement, sinds welk tijdstip) in de aanroep staat en niet in de
    constructor. Dat is nodig omdat je de scope pas kent tijdens de run,
    terwijl de provider al bij het samenstellen bestaat.
    """

    @abstractmethod
    def haal_alle_op(self, filter: F | None = None) -> Iterable[T]:
        """Haalt meerdere objecten op, eventueel afgebakend door filter.
        """
        raise NotImplementedError


class DataProvider(ObjectProvider[T], LijstProvider[T, F], ABC):
    """Voor bronnen die zowel één object als een lijst kunnen leveren."""


class DatabaseDataProvider(DataProvider[M, dict[str, Any]], ABC):
    """Provider die zijn data uit de eigen databank haalt.
    """

    identifier_veld: str = "id"

    @property
    @abstractmethod
    def model(self) -> type[M]:
        """Het model waarvan deze provider objecten ophaalt.
        """
        raise NotImplementedError

    def haal_op(self, identifier: str) -> M | None:
        return self.model.objects.filter(**{self.identifier_veld: identifier}).first()

    def haal_alle_op(self, filter: dict[str, Any] | None = None) -> QuerySet[M]:
        return self.model.objects.filter(**(filter or {}))