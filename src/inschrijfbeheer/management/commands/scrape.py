"""Management command dat de Weez-synchronisatie start.
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from inschrijfbeheer.mapping.synchronisatie import SynchronisatieConfig
from inschrijfbeheer.mapping.weez_syncer import WeezSyncer

logger = logging.getLogger("inschrijfbeheer")


class Command(BaseCommand):
    help = "Scrapet de Weez API voor het synchroniseren met de databank"

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
            help="Beperkt het aantal evenementen, handig om te proberen",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        logger.info(
            "[WEEZ SYNC] Synchronisatie opgeroepen" + (" (dry-run)" if dry_run else "")
        )

        syncer = WeezSyncer(SynchronisatieConfig(limiet=options["limiet"]))

        with transaction.atomic():
            syncer.synchroniseer()
            syncer.log_info()

            if dry_run:
                transaction.set_rollback(True)
                logger.info(
                    "[WEEZ SYNC] Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen."
                )

        self.stdout.write(self.style.SUCCESS("[WEEZ SYNC] Klaar"))