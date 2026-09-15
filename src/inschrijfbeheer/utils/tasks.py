from django.db import transaction
from procrastinate.contrib.django import app

from inschrijfbeheer.mapping.weez_syncer import WeezSyncer
from inschrijfbeheer.models import Evenement, Inschrijving
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mails
from inschrijfbeheer.utils.synchronisatie import synchroniseer_evenement



@app.task
def synchroniseer_inschrijvingen_taak(evenement_id: str):
    evenement = Evenement.objects.get(id=evenement_id)
    syncer = WeezSyncer()

    with transaction.atomic(), syncer.client:
        syncer.synchroniseer_inschrijvingen(evenement=evenement)


@app.task
def mail_attesten_taak(evenement_id: str):
    inschrijvingen = Inschrijving.objects.select_related("lid").filter(evenement=evenement_id, annulatie__isnull=True, lid__foutboodschap__isnull=True)

    maildata = []
    for inschrijving in inschrijvingen:
        maildata.append((genereer_deelname_attest(inschrijving.id), inschrijving.lid))

    stuur_attest_mails(maildata)


@app.task
def synchroniseer_evenement_taak(evenement_id: str) -> str:
    """Haalt één evenement opnieuw op bij zijn bron.
 
    Args:
        evenement_id (str): het id van het evenement, ook de identifier bij de bron
 
    Returns:
        str: de samenvatting van de synchronisatie, zichtbaar in het jobresultaat
    """
    evenement = Evenement.objects.get(id=evenement_id)
    synchroniseer_evenement(evenement)