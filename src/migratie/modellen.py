from django.db import models

class Lid(models.Model):
    id = models.CharField(primary_key=True)

# @dataclass
# class Locatie:
#     id: int
#     naam: str = None
#     huisnummer: str = None
#     postcode: str = None
#     stad: str = None

class Locatie(models.Model):
    id = models.AutoField(primary_key=True)
    naam = models.CharField()
    huisnummer = models.CharField()
    postcode = models.CharField()
    stad = models.CharField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "locatie" # geeft naam van de tabel in de nieuwe databank aan

# @dataclass
# class EvenementStatus:
#     id: int
#     beschrijving: str

class EvenementStatus(models.Model):
    id = models.AutoField(primary_key=True)
    beschrijving = models.CharField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "evenement_status" # geeft naam van de tabel in de nieuwe databank aan

# @dataclass
# class Categorie:
#     id: str
#     naam: str
#     alt_naam: str = None

class Categorie(models.Model):
    id = models.CharField(primary_key=True)
    naam = models.CharField()
    alt_naam = models.CharField()

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

class Evenement(models.Model):
    id = models.CharField(primary_key=True)
    titel = models.CharField()
    beschrijving = models.CharField()
    status = models.ForeignKey(EvenementStatus, on_delete=models.SET_NULL)
    locatie = models.ForeignKey(Locatie, on_delete=models.RESTRICT)
    starttijd = models.DateTimeField()
    eindtijd = models.DateTimeField()
    min_deelnemers = models.PositiveIntegerField()
    max_deelnemers = models.PositiveIntegerField()
    aantal_zelfde_groep = models.PositiveIntegerField()
    min_leeftijd = models.PositiveIntegerField()
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL)

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "evenement" # geeft naam van de tabel in de nieuwe databank aan

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
    id = models.CharField(primary_key=True)
    evenement = models.ForeignKey(Evenement, on_delete=models.CASCADE)
    naam = models.CharField()
    prijs = models.PositiveIntegerField()
    quota = models.PositiveIntegerField()
    starttijd_inschrijvingen = models.DateTimeField()
    eindtijd_inschrijvingen = models.DateTimeField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "deelnemertype" # geeft naam van de tabel in de nieuwe databank aan

class Inschrijving(models.Model):
    pk = models.CompositePrimaryKey("evenement", "lid")

    evenement = models.ForeignKey(Evenement, on_delete=models.RESTRICT)
    lid = models.ForeignKey(Lid, on_delete=models.RESTRICT)
    deelnemertype = models.ForeignKey(DeelnemerType, on_delete=models.RESTRICT)
    tijdstip = models.DateTimeField()
    is_betaald = models.BooleanField()
    is_geannuleerd = models.BooleanField()
    is_terugbetaald = models.BooleanField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "inschrijving" # geeft naam van de tabel in de nieuwe databank aan