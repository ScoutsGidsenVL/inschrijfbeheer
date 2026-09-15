from django.db import transaction
from procrastinate.contrib.django import app

from inschrijfbeheer.management.commands.sync import maak_weez_syncer
from inschrijfbeheer.models import Evenement, Inschrijving
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mails



@app.task
def synchroniseer_inschrijvingen_taak(evenement_id: str):
    evenement = Evenement.objects.get(id=evenement_id)
    syncer = maak_weez_syncer({"alles": None, "limiet": None})

    with transaction.atomic(), syncer.client:
        syncer.synchroniseer_inschrijvingen(evenement=evenement)

@app.task
def mail_attesten_taak(evenement_id: str):
    inschrijvingen = Inschrijving.objects.select_related("lid").filter(evenement=evenement_id, annulatie__isnull=True, lid__foutboodschap__isnull=True)

    maildata = []
    for inschrijving in inschrijvingen:
        maildata.append((genereer_deelname_attest(inschrijving.id), inschrijving.lid))

    stuur_attest_mails(maildata)