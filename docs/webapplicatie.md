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
| /oidc | django-oidc-auth |
| /docs | wordt rechtstreeks doorverwezen naar de [README](./README.md) of een bestand [docs](./) |
| /logs | wordt rechtstreeks afgehandeld door log_lijst (slechts één pad) |
| /evenementen | wordt afgehandeld door [evenementen_urls.py](../src/inschrijfbeheer/urls/evenementen_urls.py) |
| /deelnemers | wordt afgehandeld door [deelnemers_urls.py](../src/inschrijfbeheer/urls/deelnemers_urls.py) |
| /inschrijvingen | wordt afgehandeld door [inschrijvingen_urls.py](../src/inschrijfbeheer/urls/inschrijvingen_urls.py) |

Voor `/evenementen`, `/deelnemers` en `/inschrijvingen` worden de views vervolgens gedefinieerd in de corresponderende module in [inschrijfbeheer/views](../src/inschrijfbeheer/views/).

Deze views maken voor het merendeel gebruik van templates gevonden in [templates](../src/templates/). Deze templates maken gebruik van stylesheets in de directory [static](../src/static/). Deze directory bevat alle statische bestanden zoals stylesheets, afbeeldingen, scripts.