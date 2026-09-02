from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, TypeVar
from dataclasses import dataclass

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

@dataclass(frozen=True)
class IntegreatFilter:
    """Filter voor de Integreat-providers.
 
    Attributes:
        sync_alles: True haalt alles op, ongeacht wanneer het seminar eindigde.
            False beperkt tot seminars die nog bezig zijn, nog moeten
            beginnen, of minder dan terugblik_dagen afgelopen zijn.
        terugblik_dagen: hoeveel dagen na de eindtijd van een seminar er nog
            gesynchroniseerd wordt
    """
 
    sync_alles: bool = False
    terugblik_dagen: int = 30

class DatabaseDataProvider(DataProvider[M, F], ABC):
    """Provider die zijn data uit een databank haalt.
    """
 
    identifier_veld: str = "id"
 
    @property
    @abstractmethod
    def model(self) -> type[M]:
        """Het model waarvan deze provider objecten ophaalt.
        """
        raise NotImplementedError
 
    def basis_queryset(self) -> QuerySet[M]:
        """Vertrekpunt voor beide ophaalmethodes.
        """
        return self.model.objects.all()
 
    def pas_filter_toe(self, queryset: QuerySet[M], filter: F) -> QuerySet[M]:
        """Zet het filter om naar een afbakening op de queryset.
        """
        return queryset
 
    def haal_op(self, identifier: str) -> M | None:
        return self.basis_queryset().filter(**{self.identifier_veld: identifier}).first()
 
    def haal_alle_op(self, filter: F | None = None) -> QuerySet[M]:
        queryset = self.basis_queryset()
        if filter is None:
            return queryset
        return self.pas_filter_toe(queryset, filter)