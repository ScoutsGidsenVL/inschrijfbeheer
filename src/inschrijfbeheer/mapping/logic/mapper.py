"""Basisklassen voor mappers die brondata omzetten naar een Django-model."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")  # brondata
C = TypeVar("C")  # context die niet in de brondata zit
N = TypeVar("N")  # doelmodel


class MappingFout(Exception):
    """De brondata kan niet omgezet worden naar het doelmodel.
    """


@dataclass(frozen=True)
class Doelgegevens(Generic[N]):
    """Alles wat nodig is om N te bewaren, klaar voor update_or_create.

    Attributes:
        sleutels: velden die het object identificeren, de kwargs van
            update_or_create of get_or_create
        velden: velden die bij elke synchronisatie overschreven worden, de
            defaults

    """

    sleutels: dict[str, Any]
    velden: dict[str, Any] = field(default_factory=dict)


class Mapper(Generic[T, C, N], ABC):
    """Zet brondata (T) plus context (C) om naar de gegevens voor model N.

    De mapper schrijft niet naar de databank en houdt geen tellers bij, zodat
    hij een zuivere functie blijft die je zonder databank kan testen. Wat niet
    omgezet kan worden, meldt hij met MappingFout.

    De context bestaat voor alles wat het doelmodel nodig heeft maar niet in
    de brondata staat: een al bewaarde ouder, een prijzenlijst uit een ander
    endpoint, de index van een element in een lijst. Mappers die niets extra
    nodig hebben, gebruiken None als C:

        class WeezCategorieMapper(Mapper[dict, None, Categorie]):
            ...
    """

    @abstractmethod
    def map(self, bron: T, context: C) -> Doelgegevens[N]:
        """Zet één bronobject om naar de gegevens voor N.

        Raises:
            MappingFout: als de brondata onbruikbaar is
        """
        raise NotImplementedError

    def map_alle(self, bronnen: Iterable[T], context: C) -> Iterator[Doelgegevens[N]]:
        """Past map() toe op elk element met dezelfde context.

        Alleen bruikbaar wanneer de context voor alle elementen gelijk is.
        Hangt de context af van het element, zoals de volgorde van een vraag,
        dan roep je map() zelf per element aan.
        """
        return (self.map(bron, context) for bron in bronnen)