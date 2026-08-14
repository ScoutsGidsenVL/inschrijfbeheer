from django.db import models

# @dataclass
# class Evenement:
#     id: str
#     titel: str
#     beschrijving: str
#     status: int
#     locatie: int
#     starttijd: datetime
#     eindtijd: datetime
#     min_deelnemers: int
#     max_deelnemers: int
#     aantal_zelfde_groep: int
#     min_leeftijd: int
#     categorie: str # verwijst naar Categorie

class Lid(models.Model):
    pass

class Evenement(models.Model):
    pass

# @dataclass
# class DeelnemerType:
#     id: str
#     evenement: str
#     naam: str
#     prijs: int
#     quota: int
#     starttijd_inschrijving: datetime
#     eindtijd_inschrijving: datetime

class DeelnemerType(models.Model):
    pass

class Inschrijving(models.Model):
    evenement = models.ForeignKey(Evenement, on_delete=models.RESTRICT)
    lid = models.ForeignKey(Lid, on_delete=models.RESTRICT)
    deelnemertype = models.ForeignKey(DeelnemerType, on_delete=models.RESTRICT)
    tijdstip = models.DateField()
    is_betaald = models.BooleanField()
    is_geannuleerd = models.BooleanField()
    is_terugbetaald = models.BooleanField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "inschrijving" # geeft naam van de tabel in de nieuwe databank aan

# @dataclass
# class Categorie:
#     id: str
#     naam: str
#     alt_naam: str = None

# @dataclass
# class EvenementStatus:
#     id: int
#     beschrijving: str

# @dataclass
# class Locatie:
#     id: int
#     naam: str = None
#     huisnummer: str = None
#     postcode: str = None
#     stad: str = None
