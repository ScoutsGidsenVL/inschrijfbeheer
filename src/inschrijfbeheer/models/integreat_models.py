"""Module die alle relevante datamodellen voor de Integreat databank bevat.
"""
from django.db import models

class IntegreatParticipantType(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "Integreat_ParticipantType"
        managed = False

class IntegreatParticipant(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    opzoek_naam = models.CharField(db_column='LookupName')
    lid_id = models.CharField(db_column='StudentNumber')

    # Niet geïnteresseerd in andere velden -> worden genegeerd
    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "Integreat_Participant" # geeft naam van de tabel in de nieuwe databank aan
        managed = False

class IntegreatSeminarStatus(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    beschrijving = models.CharField(db_column='Description')

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "Integreat_SeminarStatus" 
        managed = False

class IntegreatSeminarType(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "Integreat_SeminarType" 
        managed = False

class IntegreatCity(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    postcode = models.CharField(db_column='Postcode')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "Integreat_City" 
        managed = False

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
    locatie_naam = models.CharField(db_column='LocationName', null=True)
    locatie_straat = models.CharField(db_column='LocationStreet', null=True)
    locatie_stad = models.ForeignKey(IntegreatCity, db_column='LocationCity', on_delete=models.DO_NOTHING, null=True)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "Integreat_Seminar"
        managed = False

class IntegreatRegistration(models.Model):
    """Integreat model voor een inschrijving

    Attributes:
        oid (int): object identifiers
        seminar (IntegreatSeminar): verwijst naar seminar waarvoor werd ingeschreven
        price (float): prijs die deelnemer betaalde. Nullable
        annulatie (datetime): datum waarop deelnemer annuleerde, annulatie is afleidbaar. Nullable
        canceledmotivation (str): reden voor annulatie. Nullable
        deelnemers_type (IntegreatParticipantType): type van de deelnemer. Nullable
        tijdstip (datetime): moment van inschrijving. Nullable
    """
    oid = models.BigIntegerField(db_column='OID', primary_key=True)
    seminar = models.ForeignKey(IntegreatSeminar, models.DO_NOTHING, db_column='Seminar', blank=True, null=True)
    deelnemer = models.ForeignKey(IntegreatParticipant, models.DO_NOTHING, db_column='Participant', blank=True, null=True)
    price = models.DecimalField(db_column='Price', max_digits=18, decimal_places=2, blank=True, null=True) 
    annulatie = models.DateTimeField(db_column='CanceledDate', blank=True, null=True)
    canceledmotivation = models.TextField(db_column='CanceledMotivation', blank=True, null=True)
    # status = models.ForeignKey('IntegreatRegistrationstatus', models.DO_NOTHING, db_column='Status', blank=True, null=True)
    deelnemers_type = models.ForeignKey(IntegreatParticipantType, models.DO_NOTHING, db_column='ParticipantType', blank=True, null=True)
    tijdstip = models.DateTimeField(db_column='RegistrationDate', blank=True, null=True)
    # organizationunitsite = models.ForeignKey('IntegreatOrganizationunitsite', models.DO_NOTHING, db_column='OrganizationUnitSite', blank=True, null=True)

    class Meta:
        app_label = "inschrijfbeheer"
        managed = False
        db_table = 'Integreat_Registration'
        unique_together = (('deelnemer', 'seminar'),)

class IntegreatSeminarFreeFieldType(models.Model):
    """Integreat model voor het type van vrije vragen.
    Mogelijke waarden zijn:
     - Checkbox
     - Radiobutton
     - Combobox
     - Date
     - Number
     - Memo
     - Preference
     - Text

    Attributes:
        oid (str): object id
        code (str): naam van het type. Nullable
        description (str): omschrijving van het type. Defaults to code. Nullable
        itemsrequired (bool): onduidelijk. Nullable
        itemsallowed (bool): onduidelijk. Nullable
    """
    oid = models.BigIntegerField(db_column='OID', primary_key=True)
    code = models.CharField(db_column='Code', max_length=50, blank=True, null=True) # identiek aan Description
    description = models.CharField(db_column='Description', max_length=50, blank=True, null=True)
    itemsrequired = models.BooleanField(db_column='ItemsRequired', blank=True, null=True)  # Onduidelijk
    itemsallowed = models.BooleanField(db_column='ItemsAllowed', blank=True, null=True)  # Onduidelijk

    class Meta:
        managed = False
        db_table = 'Integreat_SeminarFreeFieldType'

class IntegreatSeminarFreeField(models.Model):
    """Integreat model voor vrije vragen

    Attributes:
        oid (str): object id
        type (IntegreatSeminarFreeFieldType): type van de vraag. Nullable
        question (str): vraag. Nullable
        items (str): mogelijke antwoorden op de vraag (bij meerdere opties gescheiden door ';'). Nullable
        seminar (IntegreatSeminar): seminar waarvoor de vraag moet gesteld worden. Nullable
        required (bool): geeft aan of de vraag vereist is. Nullable
        sortorder (int): geeft aan in welke volgorde de vragen moeten getoond worden. Nullable
    """
    oid = models.BigIntegerField(db_column='OID', primary_key=True)
    type = models.ForeignKey(IntegreatSeminarFreeFieldType, models.DO_NOTHING, db_column='Type', blank=True, null=True)
    question = models.TextField(db_column='Caption', blank=True, null=True)
    items = models.TextField(db_column='Items', blank=True, null=True)
    seminar = models.ForeignKey(IntegreatSeminar, models.DO_NOTHING, db_column='Seminar', blank=True, null=True)
    required = models.BooleanField(db_column='Required', blank=True, null=True)
    sortorder = models.IntegerField(db_column='SortOrder', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'Integreat_SeminarFreeField'

class IntegreatRegistrationfreefield(models.Model):
    """Integreat model voor een antwoord op een vrije vraag

    Attributes:
        oid (str): object id
        field (IntegreatSeminarFreeField): verwijst naar de beantwoorde vraag. Nullable
        answer (str): antwoord op de vraag. Nullable
        registration (IntegreatRegistration): verwijst naar de inschrijving. Nullable
    """
    oid = models.BigIntegerField(db_column='OID', primary_key=True)
    field = models.ForeignKey(IntegreatSeminarFreeField, models.DO_NOTHING, db_column='Field', blank=True, null=True)
    answer = models.TextField(db_column='Answer', blank=True, null=True)
    registration = models.ForeignKey(IntegreatRegistration, models.DO_NOTHING, db_column='Registration', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Integreat_RegistrationFreeField'
