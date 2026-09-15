import logging

from django.db import transaction
from procrastinate import exceptions
from procrastinate.contrib.django import app

from inschrijfbeheer.mapping.weez_syncer import WeezSyncer
from inschrijfbeheer.models import Evenement, Inschrijving
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mails
from inschrijfbeheer.utils.synchronisatie import synchroniseer_evenement

logger = logging.getLogger(__name__)


def evenement_lock(evenement_id: str) -> str:
    """Geeft de lock waarmee alle taken van één evenement na elkaar lopen.

    Procrastinate voert nooit twee jobs met dezelfde lock tegelijk uit. Taken
    van verschillende evenementen lopen dus wel parallel.
    """
    return f"evenement:{evenement_id}"


@app.task(name="synchroniseer_inschrijvingen")
def synchroniseer_inschrijvingen_taak(evenement_id: str):
    evenement = Evenement.objects.get(id=evenement_id)
    syncer = WeezSyncer()

    with transaction.atomic(), syncer.client:
        syncer.synchroniseer_inschrijvingen(evenement=evenement)


@app.task(name="mail_attesten")
def mail_attesten_taak(evenement_id: str):
    inschrijvingen = Inschrijving.objects.select_related("lid").filter(
        evenement=evenement_id,
        annulatie__isnull=True,
        lid__foutboodschap__isnull=True,
    )

    maildata = []
    for inschrijving in inschrijvingen:
        maildata.append((genereer_deelname_attest(inschrijving.id), inschrijving.lid))

    stuur_attest_mails(maildata)


@app.task(name="synchroniseer_evenement")
def synchroniseer_evenement_taak(evenement_id: str) -> str:
    """Haalt één evenement opnieuw op bij zijn bron.

    Args:
        evenement_id (str): het id van het evenement, ook de identifier bij de bron

    Returns:
        str: de samenvatting van de synchronisatie, zichtbaar in het jobresultaat
    """
    evenement = Evenement.objects.get(id=evenement_id)
    return synchroniseer_evenement(evenement)


def defer_synchroniseer_inschrijvingen(evenement_id: str) -> int | None:
    """Plant een inschrijvingensynchronisatie in, hoogstens één in de wachtrij."""
    try:
        return synchroniseer_inschrijvingen_taak.configure(
            lock=evenement_lock(evenement_id),
            queueing_lock=f"synchroniseer_inschrijvingen:{evenement_id}",
        ).defer(evenement_id=evenement_id)
    except exceptions.AlreadyEnqueued:
        logger.info(
            "Synchronisatie van inschrijvingen staat al in de wachtrij",
            extra={"evenement_id": evenement_id},
        )
        return None


def defer_mail_attesten(evenement_id: str) -> int | None:
    """Plant de attestenmails in. Wacht tot een lopende sync van hetzelfde evenement klaar is."""
    try:
        return mail_attesten_taak.configure(
            lock=evenement_lock(evenement_id),
            queueing_lock=f"mail_attesten:{evenement_id}",
        ).defer(evenement_id=evenement_id)
    except exceptions.AlreadyEnqueued:
        logger.info(
            "Attestenmails staan al in de wachtrij",
            extra={"evenement_id": evenement_id},
        )
        return None


def defer_synchroniseer_evenement(evenement_id: str) -> int | None:
    """Plant een synchronisatie van het evenement zelf in."""
    try:
        return synchroniseer_evenement_taak.configure(
            lock=evenement_lock(evenement_id),
            queueing_lock=f"synchroniseer_evenement:{evenement_id}",
        ).defer(evenement_id=evenement_id)
    except exceptions.AlreadyEnqueued:
        logger.info(
            "Synchronisatie van het evenement staat al in de wachtrij",
            extra={"evenement_id": evenement_id},
        )
        return None