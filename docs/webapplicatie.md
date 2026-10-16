# Webapplicatie

Deze component heeft als doel om de data in de databank te visualiseren en bepaalde handelingen te doen.

## Uitvoeren

Om de applicatie uit te voeren moet men het onderstaande command uitvoeren

```shell
> cd src/
> python manage.py runserver 2197
```

## Structuur

De applicatie verdeelt de verantwoordelijkheden voor de paden van de URLs onder enkele verschillenden modules in [inschrijfbeheer/urls](../src/inschrijfbeheer/urls/). Daarbovenop zijn er enkele speciale regels voorzien voor simpele paden en afwijkende noden. Hieronder de voornaamste paden en waar de verantwoordelijkheid ligt.

| Pad | Verantwoordelijkheid |
|-----|----------------------|
| /oidc | django-oidc-auth, behalve `/oidc/frontchannel-logout/` (zie [Toegang](#toegang)) |
| /geen-toegang | pagina voor wie niet aangemeld is of geen toegang heeft |
| /docs | wordt rechtstreeks doorverwezen naar de [README](./README.md) of een bestand [docs](./) |
| /logs | wordt rechtstreeks afgehandeld door log_lijst (slechts één pad) |
| /evenementen | wordt afgehandeld door [evenementen_urls.py](../src/inschrijfbeheer/urls/evenementen_urls.py) |
| /deelnemers | wordt afgehandeld door [deelnemers_urls.py](../src/inschrijfbeheer/urls/deelnemers_urls.py) |
| /inschrijvingen | wordt afgehandeld door [inschrijvingen_urls.py](../src/inschrijfbeheer/urls/inschrijvingen_urls.py) |
| /handleidingen | wordt afgehandeld door [handleidingen_urls.py](../src/inschrijfbeheer/urls/handleidingen_urls.py) |

Voor `/evenementen`, `/deelnemers` en `/inschrijvingen` worden de views vervolgens gedefinieerd in de corresponderende module in [inschrijfbeheer/views](../src/inschrijfbeheer/views/).

Deze views maken voor het merendeel gebruik van templates gevonden in [templates](../src/templates/). Deze templates maken gebruik van stylesheets in de directory [static](../src/static/). Deze directory bevat alle statische bestanden zoals stylesheets, afbeeldingen, scripts.

## Toegang

- Je meldt aan via Keycloak (Login). Enkel personeel krijgt toegang: groep `X1027G` met de verantwoordelijkheid `personeel` in Groepsadmin.
- Die controle gebeurt bij het aanmelden en daarna opnieuw op elke pagina via `check_rollen` in [utils/auth.py](../src/inschrijfbeheer/utils/auth.py). Een geslaagde controle blijft 5 minuten geldig in de sessie.
- Alle pagina's vragen aanmelding, ook `/docs` en `/handleidingen`. Enkel `/geen-toegang`, `/oidc` en de statische bestanden zijn publiek.
- Wie geen personeel is, wordt niet bewaard in de databank.
- Meld je af bij Keycloak, dan laadt Keycloak `/oidc/frontchannel-logout/` in een verborgen iframe en word je ook hier afgemeld. Daarnaast controleert `SessionRefresh` elke minuut of je sessie bij Keycloak nog geldig is.
