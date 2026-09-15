from django.db import transaction
from procrastinate.contrib.django import app

from inschrijfbeheer.management.commands.sync import maak_weez_syncer
from inschrijfbeheer.models.inschrijfbeheer_models import Evenement



@app.task
def synchroniseer_inschrijvingen_taak(evenement: Evenement):
    syncer = maak_weez_syncer({"alles": None, "limiet": None})

    with transaction.atomic(), syncer.client:
        syncer.synchroniseer_inschrijvingen(evenement)

@app.task
def mail_attesten_taak():
    pass