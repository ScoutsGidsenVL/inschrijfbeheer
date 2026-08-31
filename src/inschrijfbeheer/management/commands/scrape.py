from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Scrapet de Weez API voor het synchroniseren met de databank"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limiet", type=int, required=False)

    def handle(self, *args, **options):
        raise CommandError("Not implemented")