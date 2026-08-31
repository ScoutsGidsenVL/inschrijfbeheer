import logging

logger = logging.getLogger("inschrijfbeheer")

from django.core.management.base import BaseCommand
from django.db import transaction

from inschrijfbeheer.mapping.mappers import (
    laad_evenementen,
    laad_deelnemertypes,
    laad_inschrijvingen,
    laad_evenement_vraagtypes,
    laad_evenement_vragen,
    laad_inschrijving_vraagantwoorden
)

QueryInfoType = tuple[int, int, int]  # aangemaakt, bijgewerkt, overgeslagen


class Command(BaseCommand):
    help = "Synchroniseert de data in de Integreat databank met de nieuwe databank"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limiet", type=int, required=False)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        logger.info(
            "[INIS SYNC] Synchronisatie opgeroepen" + (" (dry-run)" if dry_run else "")
        )

        limiet = options["limiet"] if options["limiet"] else None

        stappen = [
            ("evenementen", laad_evenementen),
            ("deelnemertypes", laad_deelnemertypes),
            ("inschrijvingen", laad_inschrijvingen),
            ("evenement vraagtypes", laad_evenement_vraagtypes),
            ("evenement vragen", laad_evenement_vragen),
            ("inschrijving antwoord", laad_inschrijving_vraagantwoorden),
        ]

        with transaction.atomic():
            for naam, functie in stappen:
                aangemaakt, bijgewerkt, overgeslagen = functie(limiet=limiet)
                logger.info(
                    f"[INIS SYNC] {naam}: aangemaakt={aangemaakt}, bijgewerkt={bijgewerkt}, overgeslagen={overgeslagen}"
                )

            if dry_run:
                transaction.set_rollback(True)
                logger.info(
                    "[INIS SYNC] Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen."
                )