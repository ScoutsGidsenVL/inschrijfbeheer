from django.core.management.base import BaseCommand
from django.db import transaction

from migratie.mappers import (
    laad_evenementen,
    laad_leden,
    # laad_deelnemertypes,
    # laad_inschrijvingen,
)

QueryInfoType = tuple[int, int, int]  # aangemaakt, bijgewerkt, overgeslagen


class Command(BaseCommand):
    help = "Synchroniseert de data in de Integreat databank met de nieuwe databank"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limiet", type=int, required=False)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            "Synchronisatie opgeroepen" + (" (dry-run)" if dry_run else "")
        )

        limiet = options["limiet"] if options["limiet"] else None

        stappen = [
            ("leden", laad_leden),
            ("evenementen", laad_evenementen),
            # ("deelnemertypes", laad_deelnemertypes),
            # ("inschrijvingen", laad_inschrijvingen),
        ]

        with transaction.atomic():
            for naam, functie in stappen:
                aangemaakt, bijgewerkt, overgeslagen = functie(limiet=limiet)
                self.stdout.write(
                    f"{naam}: aangemaakt={aangemaakt}, bijgewerkt={bijgewerkt}, "
                    f"overgeslagen={overgeslagen}"
                )

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(
                    "Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen."
                )