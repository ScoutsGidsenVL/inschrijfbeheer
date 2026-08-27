# Synchroniseer

`synchroniseer` is een Django admin commando dat de oude data van de KV en INIS uit de Integreat databank haalt en vervolgens migreert naar de nieuwe databank.
Het doet dit door gebruik te maken van Django modellen te vinden in [src/migratie/models.py](../src/migratie/models.py). De data wordt ingeladen vanuit de oude Integreat databank en vervolgens door de mapper-functies omgezet naar nieuwe objecten voor in de nieuwe databank.

## Uitvoeren

```shell
> cd src
> python manage.py synchroniseer <opties>
```

| opties | Beschrijving |
|--------|--------------|
| --limiet LIMIET | stelt een limiet in voor het aantal ingeladen objecten van iedere tabel |
| --dry-run | voer een run uit zonder weg te schrijven naar de nieuwe databank |
| --help | geef alle opties en gebruik weer |

Verder zijn ook alle standaard opties voor een Django Admin command te gebruiken. Deze zijn zichtbaar door het commando uit te voeren met `--help`