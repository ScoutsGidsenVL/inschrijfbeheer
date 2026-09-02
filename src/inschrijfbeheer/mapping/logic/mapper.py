from abc import ABC, abstractmethod
from typing import Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")
N = TypeVar("N")


class Mapper(Generic[T, N], ABC):
    """Basiscontract voor het omzetten van brondata (T) naar een domeinmodel (N).

    Elk domeinmodel uit Inschrijfbeheer krijgt zijn eigen Mapper-subklasse per
    bron, bv. WeezEvenementMapper(Mapper[dict, Evenement]).
    """

    @abstractmethod
    def map(self, bron: T) -> N:
        """Zet één object van het brontype om naar het doeltype."""
        raise NotImplementedError

    def map_alle(self, bronnen: Iterable[T]) -> Iterator[N]:
        """Past map() toe op elk element van bronnen.

        Standaardimplementatie die in de meeste subklassen niet overschreven
        hoeft te worden.
        """
        return (self.map(bron) for bron in bronnen)