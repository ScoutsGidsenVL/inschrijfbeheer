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

[settings.py](../src/inschrijfbeheer/settings.py) verwacht een aantal environment variables, dus een bestand met naam `.env` moet aangemaakt worden in de root van het project.
Dit bestand moet de volgende attributen bevatten.

```shell
DJANGO_KEY=

# attributen voor de nieuwe databank
DB_name=
DB_host=
DB_username=
DB_password=

# attributen voor de Integreat databank
INTEGREAT_DB_NAME=
INTEGREAT_DB_HOST=
INTEGREAT_DB_USER=
INTEGREAT_DB_PASSWORD=

# Keycloak configuratie
KEYCLOAK_BASE_URL=
KEYCLOAK_REALM=
KEYCLOAK_CLIENT_ID=
KEYCLOAK_CLIENT_SECRET=

# SOAP configuratie
WSDL_URL=
APPLICATIE_NAAM=
WEB_NAMESPACE=

DEELNAME_ATTEST_PDF=<pad naar template voor attest>

MAIL_RELAY_HOST=
MAIL_RELAY_PORT=
FROM_MAIL_ADRESS=<mailadres waarvan de mails zullen uitgestuurd worden>
```

## Uitvoeren

### Synchronisatie

Doordat de functionaliteit van Inschrijfbeheer uit meerdere onderdelen bestaat dienen migratie van de gegevens en het uitvoeren van de webapplicatie apart gedaan te worden.

Voor het uitvoeren van een migratie van de data van Integreat naar de databank van Inschrijfbeheer dient het commando [`synchroniseer`](./synchroniseer.md) uitgevoerd te worden.

```shell
> cd src
> python manage.py sync <weez|integreat> [--dry-run] [--limiet LIMIET] [--alles] [--terugblik-dagen TERUG_BLIKDAGEN]
> python manage.py sync --help # meer info
```

### Webapplicatie

Om de applicatie uit te voeren moet men het onderstaande command uitvoeren

```shell
> cd src/
> python manage.py runserver 2197
```

Dit opent de applicatie op [http://localhost:2197](http://localhost:2197)

Meer info over de webapplicatie is te vinden in [webapplicatie.md](./webapplicatie.md)

## Structuur

```
├── docs # documentatie
├── src
│   ├── config # bevat alle algemene configuratie in settings.py
│   ├── inschrijfbeheer
│   │   ├── assets # assets die niet bereikbaar zijn via de webapplicatie
│   │   ├── management
│   │   │   └── commands # logica voor admin commands (`sync`)
│   │   ├── mapping
│   │   │   ├── logic # alle mappers voor de synchronisatie
│   │   │   │   ├── integreat_mappers
│   │   │   │   └── weez_mappers
│   │   │   ├── providers # alle providers voor de synchronisatie
│   │   │   │   ├── integreat_providers
│   │   │   │   └── weez_providers
│   │   ├── models # alle datamodellen
│   │   ├── templatetags
│   │   ├── urls
│   │   ├── utils
│   │   └── views
│   ├── static # statische bestanden die via webapplicatie bereikbaar zijn
│   │   ├── images
│   │   └── styles
│   └── templates # HTML templates
│       ├── deelnemers
│       ├── evenementen
│       │   └── vragen
│       ├── inschrijvingen
│       ├── logging
│       └── mails
└── tests
```