# Inschrijfbeheer databank

De databank voor inschrijfbeheer is opgebouwd zodat alle data uit INIS kan geïmporteerd worden en tegelijkertijd alle data van Weezevent zonder problemen kan toegevoegd worden.

**Evenement**

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `id` | varchar | id van het evenement, dit is een string voor compatibiliteit met INIS ||
| `titel` | varchar | naam/titel van het evenement | mag niet `NULL` zijn |
| `status` | varchar | geeft de status van het evenement weer ||
| `beschrijving` | varchar | beschrijving van het evenement, niet gesaniteerd (werk van de browser) ||
| `locatie` | varchar | naam van de locatie waar het doorgaat ||
| `straat` | varchar | straat van de locatie waar het doorgaat ||
| `huisnummer` | varchar | huisnummer van de locatie waar het doorgaat | varchar omdat conversie dan niet nodig is |
| `postcode` | varchar | postcode van de gemeente/stad waar het doorgaat ||
| `stad` | varchar | stad waar het doorgaat ||
| `min_deelnemers` | int | minimaal aantal deelnemers van de activiteit | groter dan of gelijk aan 0 |
| `max_deelnemers` | int | maximaal aantal deelnemers van de activiteit | groter dan of gelijk aan 0 en groter dan `min_deelnemers` |
| `is_geannuleerd` | bool | geeft aan of de activiteit geannuleerd is | moet eventueel cascaden |
| `aantal_zelfde_groep` | int | maximale aantal mensen dat van dezelfde groep mag zijn | minimaal 0 of `NULL` |
| `min_leeftijd` | int | minimale leeftijd voor het evenement | minimaal 0 of `NULL` |
| `_is_weez` | bool | geeft aan of het evenement komt van Weezevent of niet | default `true` voor voorwaartse compatibiliteit met Weezevent |
| `_laatste_sync` | timestamp | geeft aan wanneer het evenement de laatste keer werd opgevraagd aan de API van Weezevent ||
| `categorie` | varchar | geeft aan welke categorie een evenement is ||


**Inschrijving**

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `evenement` | evenement ptr | verwijst naar het evenement waarvoor is ingeschreven | nooit `NULL` |
| `tarief` | tarief ptr | verwijst naar het betaalde tarief/deelnemerstype | nooit `NULL` |
| `lid` | varchar | ID van het lid | nooit `NULL`, eventueel validatie |
| `tijsdtip` | timestamp | tijdstip van inschrijven | standaard huidige tijd op de server |
| `is_betaald` | bool | geeft aan of het betaald is | standaard `true`, digitale betalingen |
| `is_geannuleerd` | bool | geeft aan of een ticket geannuleerd is | mogelijks cascaden als er nu te weinig mensen zijn |
| `is_terugbetaald` | bool | geeft aan of een ticket terugbetaald is | standaard `false` |
| `opmerking` | varchar | opmerking gegeven door deelnemer | |
| `vegetarisch` | bool | geeft aan of deelnemer vegetarisch is ||
| `_is_weez` | bool | geeft aan of de inschrijving komt van Weezevent of niet | default `true` voor voorwaartse compatibiliteit met Weezevent |
| `_laatste_sync` | timestamp | geeft aan wanneer de inschrijving de laatste keer werd opgevraagd aan de API van Weezevent ||