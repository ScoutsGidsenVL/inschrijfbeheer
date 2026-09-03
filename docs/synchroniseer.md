# Synchroniseer

`sync` is een Django admin commando dat de oude data van de KV en INIS uit de Integreat databank haalt of Weezevent scrapet en vervolgens migreert naar de nieuwe databank.
Het doet dit door gebruik te maken van Django modellen te vinden in [src/inschrijfbeheer/models](../src/inschrijfbeheer/models/). De data wordt ingeladen vanuit de oude Integreat databank en vervolgens door de mapper-functies omgezet naar nieuwe objecten voor in de nieuwe databank. Dit gebeurt aan de hand van `DataProviders` en `Mappers`.

Eerst zorgen de `DataProviders` voor de nodige data gegeven een aantal filters of een zekere context.
Vervolgens kunnen de `Mappers` de originele data omzetten naar de nodige nieuwe modellen.

Deze 2 klassen worden gebruikt door subklasses van [`Synchronisatie`](../src/inschrijfbeheer/mapping/synchronisatie.py). Deze klassen voeren de eigelijke synchronisatie uit.

## Uitvoeren

```shell
> cd src
> python manage.py sync <integreat|weez> <opties>
```

| opties | Beschrijving |
|--------|--------------|
| --limiet LIMIET | stelt een limiet in voor het aantal ingeladen objecten van iedere tabel |
| --dry-run | voer een run uit zonder weg te schrijven naar de nieuwe databank |
| --alles | enkel voor integreat, negeert het standaard tijdvenster en haalt alle evenementen op |
| --terugblik-dagen TERUGBLIK_DAGEN | enkel voor integreat, hoeveel dagen na de eindtijd nog gesynchroniseerd moet worden |
| --help | geef alle opties en gebruik weer |

Verder zijn ook alle standaard opties voor een Django Admin command te gebruiken. Deze zijn zichtbaar door het commando uit te voeren met `--help`

## Structuur

Alle logica wordt aangeroepen vanuit [inschrijfbeheer/management/commands/sync.py](../src/inschrijfbeheer/management/commands/sync.py). Dit is hoe Django het kan beschouwen als een admin command.

Alle logica voor de synchronisaties is te vinden in [inschrijfbeheer/mapping](../src/inschrijfbeheer/mapping/).
Deze module is zelf opgesplitst in [mapping/providers](../src/inschrijfbeheer/mapping/providers/) en [mapping/logic](../src/inschrijfbeheer/mapping/logic/).

### DataProviders

De `DataProvider` klasse biedt enkele methoden aan die gebruikt worden in de rest van de applicatie om data op te halen vanuit de bron waarvoor deze opgesteld is.

```py
@abstractmethod
def haal_op(self, identifier: str) -> T | None:

@abstractmethod
def haal_alle_op(self, filter: F | None = None) -> Iterable[T]:
```

### Mappers

De `Mapper` klasse biedt op zijn beurt enkele methoden aan die gebruikt kunnen worden om een object van type T om te zetten naar een object van type N

```py
@abstractmethod
def map(self, bron: T, context: C) -> Doelgegevens[N]:

@abstractmethod
def map_alle(self, bronnen: Iterable[T], context: C) -> Iterator[Doelgegevens[N]]:
```

Deze worden ook gebruikt in de `Synchronisatie` klassen die de synchronisatie uitvoeren.