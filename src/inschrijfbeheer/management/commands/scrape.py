from django.core.management.base import BaseCommand, CommandError
from inschrijfbeheer.utils.weez_api import maak_sessie
from inschrijfbeheer.weez_mappers import haal_weez_evenementen
from django.db import transaction


class Command(BaseCommand):
    help = "Scrapet de Weez API voor het synchroniseren met de databank"

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
            ("evenementen", haal_weez_evenementen),
        ]

        with maak_sessie() as sessie:
            with transaction.atomic():
                for naam, functie in stappen:
                    aangemaakt, bijgewerkt, overgeslagen = functie(sessie=sessie, limiet=limiet)
                    self.stdout.write(
                        f"{naam}: aangemaakt={aangemaakt}, bijgewerkt={bijgewerkt}, "
                        f"overgeslagen={overgeslagen}"
                    )

                if dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(
                        "Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen."
                    )