"""Module die alle nieuwe datamodellen voor **Inschrijfbeheer** bevat

## Classes:
    **Deelnemer:** deelnemer, gebruikt voor snellere zoekmethoden
    **EvenementStatus:** beschrijft de status van een evenement
    **Categorie:** beschrijft de categorie van een evenement
    **Evenement:** beschrijft een evenement/vorming
    **DeelnemerType:** beschrijft de rol van een deelnemer op een evenement/vorming
    **Inschrijving:** beschrijft een inschrijving voor een evenement/vorming
    **EvenementVraagType:** beschrijft het type van een vraag (checkbox/text...)
    **EvenementVraag:** vraag horende bij de inschrijvingen van een evenement
    **InschrijvingVraagAntwoord:** antwoorden van de deelnemers op de vragen
"""

from django.db import models, connection


def volgende_deelnemer_id():
    """Functie die een uniek ID genereert voor een Deelnemer.
    Dit wordt gebruikt omdat een deelnemer foutieve gegevens kan geven.

    Returns:
        str: een uniek ID
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('deelnemer_id_seq')")
        return str(cursor.fetchone()[0])


class Deelnemer(models.Model):
    """Model voor een deelnemer.
    Dit model is niet strikt nodig, als enkel het deelnemer id wordt bijgehouden in Inschrijving, 
    moet de UI steeds SOAP calls maken naar de GA wat lange wachttijden tot gevolg heeft

    Attributes:
        id (str): id van het lid uit de GA. maximale lengte van 32
        voornaam (str): voornaam van het lid
        achternaam (str): achternaam van het lid
        mailadres (str): mailadres van het lid
        foutboodschap (str): boodschap bij het lid als het foutief is. Nullable
    """
    id = models.CharField(primary_key=True, max_length=50, default=volgende_deelnemer_id)
    voornaam = models.CharField(null=False)
    achternaam = models.CharField(null=False)
    mailadres = models.CharField(null=False)
    foutboodschap = models.TextField(null=True)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "deelnemer"

    def __str__(self):
        return f"{self.voornaam} {self.achternaam}"

class EvenementStatus(models.Model):
    id = models.AutoField(primary_key=True)
    beschrijving = models.CharField()

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "evenement_status"

    def __str__(self):
        return self.beschrijving

class Categorie(models.Model):
    """Categorie van een evenement

    Attributes:
        id (str): id
        naam (str): naam van de categorie
        alt_naam (str): alternatieve naam, meestal een kopie van naam
        is_weez (str): geeft aan of de categorie van weez is
    """
    id = models.CharField(primary_key=True)
    naam = models.CharField()
    alt_naam = models.CharField()
    is_weez = models.BooleanField(default=False, blank=True)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "categorie"

    def __str__(self):
        return self.naam

class Evenement(models.Model):
    """Model voor een evenement

    Attributes:
        id (str): id van het evenement
        titel (str): titel/naam van het evenement
        beschrijving (str): beschrijving van het evenement
        status (EvenementStatus): status van het evenement. Nullable
        locatie_naam (str): naam van de locatie van het evenement. Nullable
        locatie_straat (str): straat van de locatie van het evenement. Nullable
        locatie_stad (str): stad van de locatie van het evenement. Nullable
        locatie_postcode (str): postcode van de stad van de locatie van het evenement. Nullable
        starttijd (datetime): starttijd van het evenement. Nullable
        eindtijd (datetime): eindtijd van het evenement. Nullable
        categorie (Categorie): categorie van het evenement
        is_weez (bool): geeft aan of het evenement afkomstig is van Weezevent
        laatste_sync (datetime): wanneer laatste synchronisatie was met Weez
        foutboodschap (str): geeft een foutboodschap bij een Evenement aan. Nullable
    """
    id = models.CharField(primary_key=True)
    titel = models.CharField()
    beschrijving = models.CharField()
    status = models.ForeignKey(EvenementStatus, on_delete=models.SET_NULL, null=True, db_column="status")
    locatie_naam = models.CharField(null=True, blank=True)
    locatie_straat = models.CharField(null=True, blank=True)
    locatie_stad = models.CharField(null=True, blank=True)
    locatie_postcode = models.CharField(null=True, blank=True)
    starttijd = models.DateTimeField(null=True)
    eindtijd = models.DateTimeField(null=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, db_column="categorie")
    is_weez = models.BooleanField(default=False, blank=True)
    laatste_sync = models.DateTimeField(auto_now=True)
    foutboodschap = models.TextField(null=True, blank=True)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "evenement"

    def __str__(self):
        return self.titel

class DeelnemerType(models.Model):
    id = models.CharField(primary_key=True)
    naam = models.CharField()

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "deelnemertype"

    def __str__(self):
        return self.naam

def volgend_inschrijving_id():
    """Functie die een uniek ID genereert voor een Inschrijving.
    Dit wordt gebruikt omdat Weezevent geen IDs bijhoudt voor inschrijvingen, dus deze moeten ingevuld worden.

    Returns:
        str: een uniek ID
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('inschrijving_id_seq')")
        return str(cursor.fetchone()[0])

class Inschrijving(models.Model):
    """Model voor een inschrijving

    Attributes:
        id (str): id van de inschrijving
        evenement (Evenement): evenement waarvoor werd ingeschreven
        lid (Lid): Lid object dat koppelt naar GA
        deelnemertype (DeelnemerType): type van de deelnemer. Nullable
        prijs (float): bedrag betaald door deelnemer. Nullable
        tijdstip (datetime): tijdstip van inschrijving
        annulatie (datetime): tijdstip van annulatie. Nullable, null als niet geannuleerd
        annulatie_reden (str): reden van de annulatie. Nullable, null als niet geannuleerd
        is_weez (bool): geeft aan of het gaat om een evenement van Weez. Defaults to True
    """
    id = models.CharField(primary_key=True, default=volgend_inschrijving_id)
    evenement = models.ForeignKey(Evenement, db_column="evenement", on_delete=models.RESTRICT)
    lid = models.ForeignKey(Deelnemer, db_column="lid", on_delete=models.RESTRICT)
    deelnemertype = models.ForeignKey(DeelnemerType, db_column="type", on_delete=models.SET_NULL, null=True)
    prijs = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    tijdstip = models.DateTimeField(null=True, blank=True)
    annulatie = models.DateTimeField(null=True, blank=True)
    annulatie_reden = models.TextField(null=True, blank=True)
    is_weez = models.BooleanField(default=False, blank=True)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = "inschrijving"

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
        app_label = "inschrijfbeheer"
        db_table = 'evenement_vraagtype'


def volgend_evenement_vraag_id():
    """Functie die een uniek ID genereert voor een EvenementVraag.
    Dit wordt gebruikt omdat Weezevent geen IDs bijhoudt voor vragen, dus deze moeten ingevuld worden.

    Returns:
        str: een uniek ID
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('evenement_vraag_id_seq')")
        return str(cursor.fetchone()[0])

class EvenementVraag(models.Model):
    """Model voor vrije vragen bij een evenement

    Attributes:
        id (str): id. Defaults to volgende nummer in een sequentie voor Weezevent
        type (EvenementVraagType): type van de vraag. Nullable
        vraag (str): vraag.
        items (str): mogelijke antwoorden op de vraag (bij meerdere opties gescheiden door ';'). Nullable
        evenement (Evenement): seminar waarvoor de vraag moet gesteld worden
        vereist (bool): geeft aan of de vraag vereist is. Nullable
        volgorde (int): geeft aan in welke volgorde de vragen moeten getoond worden. Nullable
    """
    id = models.CharField(primary_key=True, default=volgend_evenement_vraag_id)
    type = models.ForeignKey(EvenementVraagType, models.DO_NOTHING, blank=True, null=True)
    vraag = models.TextField()
    items = models.TextField(blank=True, null=True)
    evenement = models.ForeignKey(Evenement, models.CASCADE)
    vereist = models.BooleanField(blank=True, null=True)
    volgorde = models.IntegerField(blank=True, null=True)
    class Meta:
        app_label = "inschrijfbeheer"
        db_table = 'evenement_vraag'

def volgend_inschrijving_vraagantwoord_id() -> str:
    """Functie die een uniek ID genereert voor een InschrijvingVraagAntwoord.
    Dit wordt gebruikt omdat Weezevent geen IDs bijhoudt voor vragen, dus deze moeten ingevuld worden.

    Returns:
        str: een uniek ID
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('inschrijving_vraagantwoord_id_seq')")
        return str(cursor.fetchone()[0])

class InschrijvingVraagAntwoord(models.Model):
    """Model voor een antwoord op een vrije vraag bij een evenement

    Attributes:
        id (int): id. Defaults to volgende nummer in een sequentie voor Weezevent
        vraag (EvenementVraag): verwijst naar de beantwoorde vraag. Nullable
        antwoord (str): antwoord op de vraag. Nullable
        inschrijving (Inschrijving): verwijst naar de inschrijving. Nullable
    """
    id = models.CharField(primary_key=True, default=volgend_inschrijving_vraagantwoord_id)
    vraag = models.ForeignKey(EvenementVraag, models.CASCADE)
    antwoord = models.TextField(blank=True, null=True)
    inschrijving = models.ForeignKey(Inschrijving, models.CASCADE)

    class Meta:
        app_label = "inschrijfbeheer"
        db_table = 'inschrijving_vraagantwoord'
