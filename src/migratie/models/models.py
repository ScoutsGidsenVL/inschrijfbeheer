from django.db import models


"""
Modellen voor de nieuwe databank die Integreat zal vervangen, momenteel redelijk compact
"""

class Locatie(models.Model):
    id = models.AutoField(primary_key=True)
    naam = models.CharField(null=True)
    straat = models.CharField(null=True)
    huisnummer = models.CharField(null=True)
    postcode = models.CharField(null=True)
    stad = models.CharField(null=True)

    models.CheckConstraint(
        condition=(
            models.Q(naam__isnull=False) |
            models.Q(straat__isnull=False, huisnummer__isnull=False, postcode__isnull=False, stad__isnull=False)
        ),
        name="locatie_of_adres"
    )

    class Meta:
        app_label = "migratie"
        db_table = "locatie" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        if self.naam:
            return self.naam
        return f"{self.straat} {self.huisnummer}, {self.postcode} {self.stad}"

class EvenementStatus(models.Model):
    id = models.AutoField(primary_key=True)
    beschrijving = models.CharField()

    class Meta:
        app_label = "migratie"
        db_table = "evenement_status" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return self.beschrijving

class Categorie(models.Model):
    id = models.CharField(primary_key=True)
    naam = models.CharField()
    alt_naam = models.CharField()

    class Meta:
        app_label = "migratie"
        db_table = "categorie" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return self.naam

class Evenement(models.Model):
    id = models.CharField(primary_key=True)
    titel = models.CharField()
    beschrijving = models.CharField()
    status = models.ForeignKey(EvenementStatus, on_delete=models.SET_NULL, null=True, db_column="status")
    locatie = models.ForeignKey(Locatie, on_delete=models.RESTRICT, null=True, db_column="locatie")
    starttijd = models.DateTimeField()
    eindtijd = models.DateTimeField()
    min_deelnemers = models.PositiveIntegerField()
    max_deelnemers = models.PositiveIntegerField()
    aantal_zelfde_groep = models.PositiveIntegerField()
    min_leeftijd = models.PositiveIntegerField()
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, db_column="categorie")

    class Meta:
        app_label = "migratie"
        db_table = "evenement" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return self.titel

class DeelnemerType(models.Model):
    id = models.CharField(primary_key=True)
    naam = models.CharField()
    prijs = models.PositiveIntegerField()
    quota = models.PositiveIntegerField()
    starttijd_inschrijvingen = models.DateTimeField()
    eindtijd_inschrijvingen = models.DateTimeField()

    class Meta:
        app_label = "migratie"
        db_table = "deelnemertype" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return self.naam

class Inschrijving(models.Model):
    id = models.CharField(primary_key=True)
    evenement = models.ForeignKey(Evenement, db_column="evenement", on_delete=models.RESTRICT)
    lid = models.CharField()
    deelnemertype = models.ForeignKey(DeelnemerType, db_column="type", on_delete=models.RESTRICT)
    tijdstip = models.DateTimeField()
    is_betaald = models.BooleanField()
    is_geannuleerd = models.BooleanField()
    is_terugbetaald = models.BooleanField()

    class Meta:
        unique_together = (('evenement', 'lid')) # Django 5.1 ondersteund geen composite primary keys
        app_label = "migratie"
        db_table = "inschrijving" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return self.lid


class EvenementVraagType(models.Model):
    """Model voor het type van vrije vragen bij een evenement

    Attributes:
        naam (str): naam van het type. Primaire sleutel
        items_vereist (bool): onduidelijk. Nullable
        items_toegestaan (bool): onduidelijk. Nullable
    """
    naam = models.CharField(primary_key=True, db_column='Code', max_length=50)
    items_vereist = models.BooleanField(blank=True, null=True)
    items_toegestaan = models.BooleanField(blank=True, null=True)

    class Meta:
        app_label = "migratie"
        db_table = 'evenement_vraagtype'

class EvenementVraag(models.Model):
    """Model voor vrije vragen bij een evenement

    Attributes:
        id (int): automatisch id voor in de databank
        type (EvenementVraagType): type van de vraag. Nullable
        vraag (str): vraag.
        items (str): mogelijke antwoorden op de vraag (bij meerdere opties gescheiden door ';'). Nullable
        evenement (Evenement): seminar waarvoor de vraag moet gesteld worden
        vereist (bool): geeft aan of de vraag vereist is. Nullable
        volgorde (int): geeft aan in welke volgorde de vragen moeten getoond worden. Nullable
    """
    id = models.CharField(primary_key=True)
    type = models.ForeignKey(EvenementVraagType, models.DO_NOTHING, blank=True, null=True)
    vraag = models.TextField()
    items = models.TextField(blank=True, null=True)
    evenement = models.ForeignKey(Evenement, models.CASCADE)
    vereist = models.BooleanField(blank=True, null=True)
    volgorde = models.IntegerField(blank=True, null=True)
    class Meta:
        app_label = "migratie"
        db_table = 'evenement_vraag'

class InschrijvingVraagAntwoord(models.Model):
    """Model voor een antwoord op een vrije vraag bij een evenement

    Attributes:
        id (int): automatisch id voor in de databank
        vraag (EvenementVraag): verwijst naar de beantwoorde vraag. Nullable
        antwoord (str): antwoord op de vraag. Nullable
        inschrijving (Inschrijving): verwijst naar de inschrijving. Nullable
    """
    id = models.AutoField(primary_key=True)
    vraag = models.ForeignKey(EvenementVraag, models.CASCADE)
    antwoord = models.TextField(blank=True, null=True)
    inschrijving = models.ForeignKey(Inschrijving, models.CASCADE)

    class Meta:
        app_label = "migratie"
        db_table = 'inschrijving_vraagantwoord'


"""
Modellen voor de oude databank van Integreat
"""

class IntegreatParticipantType(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_ParticipantType"
        managed = False

class IntegreatParticipant(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    opzoek_naam = models.CharField(db_column='LookupName')
    lid_id = models.CharField(db_column='StudentNumber')

    # Niet geïnteresseerd in andere velden -> worden genegeerd
    class Meta:
        app_label = "migratie"
        db_table = "Integreat_Participant" # geeft naam van de tabel in de nieuwe databank aan
        managed = False

class IntegreatSeminarStatus(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    beschrijving = models.CharField(db_column='Description')

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_SeminarStatus" 
        managed = False

class IntegreatSeminarType(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='Code')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_SeminarType" 
        managed = False

class IntegreatCity(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    postcode = models.CharField(db_column='Postcode')
    naam = models.CharField(db_column='Name')

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_City" 
        managed = False

class IntegreatOrganisationUnit(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    code = models.CharField(db_column='')

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_OrganizationUnit" 
        managed = False

class IntegreatOrganisationUnitSite(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    organisatie = models.ForeignKey(IntegreatOrganisationUnit, db_column='OrganizationUnit', on_delete=models.DO_NOTHING)

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_OrganizationUnitLocation" 
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
    organisator = models.ForeignKey(IntegreatOrganisationUnitSite, db_column='OrganizationUnitSite', on_delete=models.DO_NOTHING)
    locatie_naam = models.CharField(db_column='LocationName', null=True)
    locatie_straat = models.CharField(db_column='LocationStreet', null=True)
    locatie_stad = models.ForeignKey(IntegreatCity, db_column='LocationCity', on_delete=models.DO_NOTHING, null=True)

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_Seminar"
        managed = False

class IntegreatRegistration(models.Model):
    oid = models.PositiveIntegerField(primary_key=True, db_column='OID')
    seminar = models.ForeignKey(IntegreatSeminar, db_column="Seminar", on_delete=models.RESTRICT)
    deelnemers_type = models.ForeignKey(IntegreatParticipantType, db_column="ParticipantType", on_delete=models.RESTRICT)
    deelnemer = models.ForeignKey(IntegreatParticipant, db_column="Participant", on_delete=models.RESTRICT)
    tijdstip = models.DateTimeField(db_column="CreatedOn")
    annulatie = models.DateTimeField(db_column="CanceledDate", null=True)

    class Meta:
        app_label = "migratie"
        db_table = "Integreat_Registration"
        managed = False

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

class IntegreatSalesInvoicedetail(models.Model):
    """Integreat model voor een betalingsdetail.
    Dit bevat betaalde bedragen, dus wordt gebruikt voor te bepalen hoeveel een gebruiker betaalde voor een vorming.

    Attributes:
        oid (str): object identifier
        unitprice (float): betaalde bedrag
        seminar (IntegreatSeminar): seminar waarvoor er betaald werd
        registration (IntegreatRegistration): verwijst naar de inschrijving
        createdon (datetime): verwijst naar het tijdstip van betaling
        nettoamount (float): betaalde netto bedrag (equivalent aan totaalbedrag)
        totalamount (float): betaalde totaal bedrag (equivalent aan nettoamount)
    """
    oid = models.BigIntegerField(db_column='OID', primary_key=True)
    # header = models.ForeignKey('IntegreatSalesInvoice', models.DO_NOTHING, db_column='Header', blank=True, null=True) # ticketinfo
    # article = models.ForeignKey('IntegreatArticle', models.DO_NOTHING, db_column='Article', blank=True, null=True)  # Artikel is steeds een vorming
    unitprice = models.DecimalField(db_column='UnitPrice', max_digits=18, decimal_places=4, blank=True, null=True)  # BELANGRIJK BEVAT BETAALD BEDRAG
    participant = models.ForeignKey(IntegreatParticipant, models.DO_NOTHING, db_column='Participant', blank=True, null=True)  # afleidbaar
    seminar = models.ForeignKey(IntegreatSeminar, models.DO_NOTHING, db_column='Seminar', blank=True, null=True)  # afleidbaar
    registration = models.ForeignKey(IntegreatRegistration, models.DO_NOTHING, db_column='Registration', blank=True, null=True)  # BELANGRIJK BEVAT INSCHRIJVING
    createdon = models.DateTimeField(db_column='CreatedOn', blank=True, null=True)  # Wanneer betaald werd??
    nettoamount = models.DecimalField(db_column='NettoAmount', max_digits=18, decimal_places=4, blank=True, null=True)  # duplicate voor bedrag
    totalamount = models.DecimalField(db_column='TotalAmount', max_digits=18, decimal_places=4, blank=True, null=True)  # duplicate voor bedrag

    class Meta:
        managed = False
        db_table = 'Integreat_Sales_InvoiceDetail'