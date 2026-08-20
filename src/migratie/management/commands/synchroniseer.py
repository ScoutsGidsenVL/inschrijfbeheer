from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Synchroniseert de data in de Integreat databank met de nieuwe databank"

    def handle(self, *args, **options):
        self.stdout.write("Synchronisatie opgeroepen")
