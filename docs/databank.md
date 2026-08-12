# Inschrijfbeheer databank

De databank voor inschrijfbeheer is opgebouwd zodat alle data uit INIS kan geïmporteerd worden en tegelijkertijd alle data van Weezevent zonder problemen kan toegevoegd worden.

## INIS Databank

**Integreat_Participant** -> leden en deelnemers<br>Mogelijk om 90% van de kolommen te verwijderen<br>StudentNumber -> __lid ID__

**Integreat_Client** -> gedeelte deelnemers, maar geen volledige overlap, minder relevante gegevens

**Integreat_Registration** -> koppeling tussen persoon en evenement, eventueel betaald bedrag

**Integreat_OrganizationUnitSite** -> Groep waarvoor persoon zich inschrijft

**Integreat_ParticipantType** -> type waarin de persoon meedeed

**Integreat_ParticipantFamily** -> contacten? geen duidelijke links naar personen

**Integreat_ParticipantGroup** -> meer info over groep

**Integreat_ParticipantStatus** -> 5 vaste waarden voor status deelnemer

**Integreat_Seminar** -> info over het evenement

**Seminar_FreeField** -> vrije vragen hangen vast aan event

**Integreat_RegistrationFreeField** -> antwoorden op vrije vragen, hangt aan registration en freefield

## Inschrijfbeheer databank

#### evenement

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
| `categorie` | [categorie](#categorie) | geeft aan welke categorie een evenement is ||


#### inschrijving

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `evenement` | [evenement](#evenement) | verwijst naar het evenement waarvoor is ingeschreven | nooit `NULL` |
| `tarief` | [tarief](#tarief) | verwijst naar het betaalde tarief/deelnemerstype | nooit `NULL` |
| `lid` | varchar | ID van het lid | nooit `NULL`, eventueel validatie |
| `tijsdtip` | timestamp | tijdstip van inschrijven | standaard huidige tijd van de databank |
| `is_betaald` | bool | geeft aan of het betaald is | standaard `true`, digitale betalingen |
| `is_geannuleerd` | bool | geeft aan of een ticket geannuleerd is | mogelijks cascaden als er nu te weinig mensen zijn |
| `is_terugbetaald` | bool | geeft aan of een ticket terugbetaald is | standaard `false` |
| `opmerking` | varchar | opmerking gegeven door deelnemer | |
| `vegetarisch` | bool | geeft aan of deelnemer vegetarisch is ||
| `_is_weez` | bool | geeft aan of de inschrijving komt van Weezevent of niet | default `true` voor voorwaartse compatibiliteit met Weezevent |
| `_laatste_sync` | timestamp | geeft aan wanneer de inschrijving de laatste keer werd opgevraagd aan de API van Weezevent ||

#### tarief

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `id` | varchar | id van het tarief/deelnemerstype, wordt gegeven door Weezevent | primary key |
| `naam` | varchar | naam van het tarief/deelnemerstype ||
| `prijs` | int | prijs van het tarief/deelnemerstype | moet positief zijn |
| `quota` | int | quotum van het tarief om te behalen | moet positief zijn |
| `starttijd_inschrijvingen` | timestamp | geeft aan wanneer inschrijvingen voor dit tarief beginnen | standaard huidige tijd van de databank |
| `eindtijd_inschrijvingen` | timestamp | geeft aan wanneer inschrijvingen voor dit tarief eindigen | moet strikt groter zijn dan `starttijd_inschrijvingen` |
| `_is_weez` | bool | geeft aan of het tarief komt van Weezevent of niet | default `true` voor voorwaartse compatibiliteit met Weezevent |
| `_laatste_sync` | timestamp | geeft aan wanneer het tarief de laatste keer werd opgevraagd aan de API van Weezevent ||
| `evenement` | [evenement](#evenement) | evenement waar het tarief bijhoort ||

#### categorie

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `id` | varchar | id van de categorie ||
| `naam` | varchar | naam van de categorie | moet uniek zijn en niet `NULL`, eventueel aanpassen moesten oude categorieën overlap tonen met categoriën Weezevent ||
| `alt_naam` | varchar | alternatieve benaming voor categorie ||
| `_is_weez` | bool | geeft aan of de categorie komt van Weezevent of niet | default `true` voor voorwaartse compatibiliteit met Weezevent |
| `_laatste_sync` | timestamp | geeft aan wanneer de categorie de laatste keer werd opgevraagd aan de API van Weezevent ||

#### evenement_datum

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `evenement` | [evenement](#evenement) | evenement waar data bij horen ||
| `starttijd` | timestamp | start van het evenement | nooit `NULL`, moet uniek zijn in combinatie met evenement |
| `eindtijd` | timestamp | eind van het evenement | nooit `NULL`, strikt groter dan `starttijd` |
| `_is_weez` | bool | geeft aan of de datum komt van Weezevent of niet | default `true` voor voorwaartse compatibiliteit met Weezevent |
| `_laatste_sync` | timestamp | geeft aan wanneer de datum de laatste keer werd opgevraagd aan de API van Weezevent ||

#### inschrijving_vraag

| Attribuut | Datatype | Uitleg | Opmerkingen |
|-----------|----------|--------|-------------|
| `inschrijving` | [inschrijving](#inschrijving) | inschrijving waar vraag bij gesteld werd ||
| `vraag` | varchar || wordt gebruikt in primary key -> pseudo ID instellen |
| `antwoord` | varchar | antwoord op de vraag ||