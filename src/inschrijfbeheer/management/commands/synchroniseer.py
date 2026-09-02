"""Management command dat de Integreat-synchronisatie start.

De bestandsnaam bepaalt de naam van het commando:
    inschrijfbeheer/management/commands/integreat_sync.py -> manage.py integreat_sync
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from inschrijfbeheer.mapping.integreat_syncer import IntegreatProviders, IntegreatSyncer
from inschrijfbeheer.mapping.synchronisatie import SynchronisatieConfig

from inschrijfbeheer.mapping.data.integreat_providers import (
    IntegreatSeminarProvider,
    IntegreatParticipantTypeProvider,
    IntegreatSeminarFreeFieldTypeProvider,
    IntegreatSeminarFreeFieldProvider,
    IntegreatRegistrationProvider,
    IntegreatRegistrationfreefieldProvider,
)
from inschrijfbeheer.mapping.data.data_provider import IntegreatFilter
from inschrijfbeheer.mapping.data.lid_provider import LidProvider

logger = logging.getLogger("inschrijfbeheer")


def maak_providers() -> IntegreatProviders:
    """Stelt de providers samen.

    Dit hoort hier en niet in IntegreatSyncer, zodat je in een test dezelfde
    syncer met nagemaakte providers kan gebruiken.
    """
    return IntegreatProviders(
        seminars=IntegreatSeminarProvider(),
        deelnemertypes=IntegreatParticipantTypeProvider(),
        vraagtypes=IntegreatSeminarFreeFieldTypeProvider(),
        vragen=IntegreatSeminarFreeFieldProvider(),
        registraties=IntegreatRegistrationProvider(),
        antwoorden=IntegreatRegistrationfreefieldProvider(),
        leden=LidProvider(),
    )


class Command(BaseCommand):
    help = "Zet de records uit de Integreat-databank om naar de nieuwe modellen"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Voert alles uit maar draait de wijzigingen achteraf terug",
        )
        parser.add_argument(
            "--limiet",
            type=int,
            default=None,
            help=(
                "Beperkt het aantal records per soort. Let op: de limiet geldt per "
                "provider, dus de eerste registraties horen niet noodzakelijk bij de "
                "eerste seminars. Verwacht dus veel overgeslagen records"
            ),
        )
        parser.add_argument(
            "--alles",
            action="store_true",
            help="Negeert het terugblikvenster en haalt ook oude seminars op",
        )
        parser.add_argument(
            "--terugblik-dagen",
            type=int,
            default=None,
            help="Hoeveel dagen na de eindtijd van een seminar er nog gesynchroniseerd wordt",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        logger.info(
            "[INTEGREAT SYNC] Synchronisatie opgeroepen" + (" (dry-run)" if dry_run else "")
        )

        limiet = options["limiet"]
        filter_velden = {"sync_alles": options["alles"], "limiet": limiet}
        if options["terugblik_dagen"] is not None:
            filter_velden["terugblik_dagen"] = options["terugblik_dagen"]

        syncer = IntegreatSyncer(
            providers=maak_providers(),
            sync_config=SynchronisatieConfig(limiet=limiet),
            bron_filter=IntegreatFilter(**filter_velden),
        )

        with transaction.atomic():
            syncer.synchroniseer()
            syncer.log_info()

            if dry_run:
                transaction.set_rollback(True)
                logger.info(
                    "[INTEGREAT SYNC] Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen."
                )

        self.stdout.write(self.style.SUCCESS("[INTEGREAT SYNC] Klaar"))