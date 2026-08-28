from django.db import models


"""
Modellen voor de nieuwe databank die Integreat zal vervangen, momenteel redelijk compact
"""

class Lid(models.Model):
    """Model voor een lid.
    Dit model is niet strikt nodig, als enkel het lid id wordt bijgehouden in Inschrijving, 
    moet de UI steeds SOAP calls maken naar de GA wat lange wachttijden tot gevolg heeft

    Attributes:
        id (str): id van het lid uit de GA. maximale lengte van 32
        voornaam (str): voornaam van het lid
        achternaam (str): achternaam van het lid
        mailadres (str): mailadres van het lid
    """
    id = models.CharField(primary_key=True, max_length=32)
    voornaam = models.CharField(null=False)
    achternaam = models.CharField(null=False)
    mailadres = models.CharField(null=False)

    class Meta:
        app_label = "migratie"
        db_table = "lid" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return f"{self.voornaam} {self.achternaam}"

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
    """Model voor een inschrijving

    Attributes:
        id (str): id van de inschrijving
        evenement (Evenement): evenement waarvoor werd ingeschreven
        lid (str): lid id uit de groepsadmin voor identificatie lid
        deelnemertype (DeelnemerType): type van de deelnemer. Nullable
        prijs (float): bedrag betaald door deelnemer. Nullable
        tijdstip (datetime): tijdstip van inschrijving
        annulatie (datetime): tijdstip van annulatie. Nullable, null als niet geannuleerd
        annulatie_reden (str): reden van de annulatie. Nullable, null als niet geannuleerd
    """
    id = models.CharField(primary_key=True)
    evenement = models.ForeignKey(Evenement, db_column="evenement", on_delete=models.RESTRICT)
    lid = models.ForeignKey(Lid, db_column="lid", on_delete=models.RESTRICT)
    deelnemertype = models.ForeignKey(DeelnemerType, db_column="type", on_delete=models.SET_NULL, null=True)
    prijs = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    tijdstip = models.DateTimeField()
    annulatie = models.DateTimeField(null=True, blank=True)
    annulatie_reden = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (('evenement', 'lid')) # Django 5.1 ondersteund geen composite primary keys
        app_label = "migratie"
        db_table = "inschrijving" # geeft naam van de tabel in de nieuwe databank aan

    def __str__(self):
        return str(self.lid)


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
    id = models.CharField(primary_key=True)
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
        app_label = "migratie"
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
