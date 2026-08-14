from dataclasses import dataclass
from datetime import datetime

@dataclass
class Inschrijving:
    evenement: str
    lid: str
    deelnemertype: str
    tijdstip: datetime
    is_betaald: bool
    is_geannuleerd: bool
    is_terugbetaald: bool

@dataclass
class DeelnemerType:
    id: str
    evenement: str
    naam: str
    prijs: int
    quota: int
    starttijd_inschrijving: datetime
    eindtijd_inschrijving: datetime

@dataclass
class Evenement:
    id: str
    titel: str
    beschrijving: str
    status: int
    locatie: int
    starttijd: datetime
    eindtijd: datetime
    min_deelnemers: int
    max_deelnemers: int
    aantal_zelfde_groep: int
    min_leeftijd: int
    categorie: str # verwijst naar Categorie

@dataclass
class Categorie:
    id: str
    naam: str
    alt_naam: str = None

@dataclass
class EvenementStatus:
    id: int
    beschrijving: str

@dataclass
class Locatie:
    id: int
    naam: str = None
    huisnummer: str = None
    postcode: str = None
    stad: str = None
