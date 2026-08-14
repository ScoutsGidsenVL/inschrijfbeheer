from django.db import models


"""
Modellen voor de nieuwe databank die Integreat zal vervangen, momenteel redelijk compact
"""

class Lid(models.Model):
    id = models.CharField(primary_key=True)

    class Meta:
        app_label = "Integreat_migratie"

class Locatie(models.Model):
    id = models.AutoField(primary_key=True)
    naam = models.CharField()
    huisnummer = models.CharField()
    postcode = models.CharField()
    stad = models.CharField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "locatie" # geeft naam van de tabel in de nieuwe databank aan

class EvenementStatus(models.Model):
    id = models.AutoField(primary_key=True)
    beschrijving = models.CharField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "evenement_status" # geeft naam van de tabel in de nieuwe databank aan

class Categorie(models.Model):
    id = models.CharField(primary_key=True)
    naam = models.CharField()
    alt_naam = models.CharField()

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "evenement_categorie" # geeft naam van de tabel in de nieuwe databank aan

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
    evenement = models.ForeignKey(Evenement, on_delete=models.RESTRICT)
    lid = models.ForeignKey(Lid, on_delete=models.RESTRICT)
    deelnemertype = models.ForeignKey(DeelnemerType, on_delete=models.RESTRICT)
    tijdstip = models.DateTimeField()
    is_betaald = models.BooleanField()
    is_geannuleerd = models.BooleanField()
    is_terugbetaald = models.BooleanField()

    class Meta:
        unique_together = (('evenement', 'lid')) # Django 5.1 ondersteund geen composite primary keys
        app_label = "Integreat_migratie"
        db_table = "inschrijving" # geeft naam van de tabel in de nieuwe databank aan


"""
Modellen voor de oude databank van Integreat
"""

class IntegreatParticipant(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    opzoek_naam = models.CharField(db_column='LookupName')
    lid_id = models.CharField(db_column='StudentNumber')

    # Niet geïnteresseerd in andere velden -> worden genegeerd
    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_Participant" # geeft naam van de tabel in de nieuwe databank aan

class IntegreatSeminarStatus(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    beschrijving = models.CharField(db_column='Description')

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_SeminarStatus" 

class IntegreatSeminarType(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_SeminarType" 

class IntegreatLocationCity(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    postcode = models.CharField(db_column='Postcode')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_LocationCity" 

class IntegreatOrganisationUnit(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='')

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_OrganizationUnit" 

class IntegreatOrganisationUnitSite(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    organisatie = models.ForeignKey(IntegreatOrganisationUnit, db_column='OrganizationUnit', on_delete=models.DO_NOTHING)

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_OrganizationUnitLocation" 

class IntegreatSeminar(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    naam = models.CharField(db_column='Name')
    onderwerp = models.CharField(db_column='Subject')
    starttijd = models.DateTimeField(db_column='StartTime')
    eindtijd = models.DateTimeField(db_column='EndTime')
    eind_inschrijvingen = models.DateTimeField(db_column='EndRegistration')
    status = models.ForeignKey(IntegreatSeminarStatus, db_column='Status', on_delete=models.DO_NOTHING)
    type = models.ForeignKey(IntegreatSeminarType, db_column='Type', on_delete=models.DO_NOTHING)
    organisator = models.ForeignKey(IntegreatOrganisationUnitSite, db_column='OrganizerUnitSite', on_delete=models.DO_NOTHING)
    locatie_naam = models.CharField(db_column='LocationName')
    locatie_straat = models.CharField(db_column='LocationStreet')
    locatie_stad = models.ForeignKey(IntegreatLocationCity, db_column='LocationCity', on_delete=models.DO_NOTHING)

    class Meta:
        app_label = "Integreat_migratie"
        db_table = "Integreat_Seminar" 