import logging
import os

from django.db import transaction
from dotenv import load_dotenv
from procrastinate import exceptions
from procrastinate.contrib.django import app

from inschrijfbeheer.mapping.integreat_syncer import IntegreatSyncer
from inschrijfbeheer.mapping.utils.synchronisatie import SynchronisatieConfig
from inschrijfbeheer.mapping.weez_syncer import WeezSyncer
from inschrijfbeheer.models import Evenement, Inschrijving
from inschrijfbeheer.utils.attesten import genereer_deelname_attest
from inschrijfbeheer.utils.mailer import stuur_attest_mails
from inschrijfbeheer.utils.synchronisatie import synchroniseer_evenement

logger = logging.getLogger(__name__)

load_dotenv()
TERUGBLIK_DAGEN = os.getenv("INTEGREAT_TERUGBLIK_DAGEN")


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
    inschrijvingen = Inschrijving.objects.select_related("lid", "evenement").filter(
        evenement=evenement_id,
        annulatie__isnull=True,
        registratie=True,
        lid__foutboodschap__isnull=True,
        evenement__foutboodschap__isnull=True,
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


BRON_LOCK = "synchronisatie:weez"


@app.periodic(cron="0 * * * *")
@app.task(
    name="uurlijkse_synchronisatie",
    lock=BRON_LOCK,
    queueing_lock="uurlijkse_synchronisatie",
    pass_context=False,
)
def uurlijkse_synchronisatie_taak(timestamp: int) -> str:
    """Draait elk uur een volledige synchronisatie bij de bron.

    De `lock` houdt twee runs uit elkaar, ook als een run langer duurt dan een
    uur. De `queueing_lock` zorgt dat er ondertussen hoogstens één run in de
    wachtrij staat in plaats van een stapel.

    De `timestamp` komt van Procrastinate en bevat het geplande uur als
    unix-timestamp.

    Args:
        timestamp (int): het uur waarvoor deze run gepland stond

    Returns:
        str: de samenvatting van de synchronisatie, zichtbaar in het jobresultaat
    """
    config = SynchronisatieConfig(
        sync_alles=False,
        dry_run=False,
        terugblik_dagen=TERUGBLIK_DAGEN,
    )

    weez_syncer = WeezSyncer(config=config)
    integreat_syncer = IntegreatSyncer(config=config)

    logger.info(
        "Start uurlijkse synchronisatie",
        extra={"timestamp": timestamp, "terugblik_dagen": config.terugblik_dagen},
    )

    weez_syncer.voer_uit()
    integreat_syncer.voer_uit()

    logger.info(
        "Uurlijkse synchronisatie klaar",
        extra={"timestamp": timestamp},
    )
