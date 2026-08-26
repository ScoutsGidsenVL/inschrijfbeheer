# Inschrijfbeheer

## Opzet

Alle dependencies zijn te vinden in [requirements.txt](../requirements.txt). Het opzetten van de virtuele omgeving gebeurt aan de hand van de volgende commandos op een Linux systeem.

```shell
# opzetten van de virtuele omgeving
> python3 -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt

# opzetten databank
> cd src
> python manage.py makemigrations
> python manage.py migrate
```

## Uitvoeren

Doordat de functionaliteit van Inschrijfbeheer uit meerdere onderdelen bestaat dienen migratie van de gegevens en het uitvoeren van de webapplicatie apart gedaan te worden.

Voor het uitvoeren van een migratie van de data van Integreat naar de databank van Inschrijfbeheer dient het commando [`synchroniseer`](./synchroniseer.md) uitgevoerd te worden.

```shell
> cd src
> python manage.py synchroniseer [--dry-run] [--limiet LIMIET]
> python manage.py synchroniseer --help # meer info
```