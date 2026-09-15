"""Management command dat een synchronisatie start, voor Weez of Integreat.

De bestandsnaam bepaalt de naam van het commando:
    inschrijfbeheer/management/commands/sync.py -> manage.py sync

    manage.py sync weez
    manage.py sync integreat --alles
    manage.py sync weez integreat --dry-run

Dit commando kent alleen de commandoregel. Het zet je opties om naar een
SynchronisatieConfig en geeft die aan de syncer. Welke providers en onderdelen
daarbij horen, regelt elke syncer zelf.
"""

from django.core.management.base import BaseCommand

from inschrijfbeheer.mapping.integreat_syncer import IntegreatSyncer
from inschrijfbeheer.mapping.synchronisatie import Synchronisatie, SynchronisatieConfig
from inschrijfbeheer.mapping.weez_syncer import WeezSyncer

BRONNEN: dict[str, type[Synchronisatie]] = {
    syncer.naam: syncer for syncer in (WeezSyncer, IntegreatSyncer)
}


class Command(BaseCommand):
    help = "Synchroniseert de gekozen databron met de databank"

    def add_arguments(self, parser):
        parser.add_argument(
            "bron",
            nargs="+",
            choices=sorted(BRONNEN),
            help="Welke bron je synchroniseert. Je mag er ook meer dan één opgeven",
        )
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
                "Beperkt het aantal records, handig om te proberen. Bij weez is dat "
                "het aantal evenementen. Bij integreat geldt de limiet per soort "
                "record, dus de eerste registraties horen niet noodzakelijk bij de "
                "eerste seminars en mag je veel overgeslagen records verwachten"
            ),
        )
        parser.add_argument(
            "--alles",
            action="store_true",
            help="Negeert het terugblikvenster en haalt ook oude evenementen op",
        )
        parser.add_argument(
            "--terugblik-dagen",
            type=int,
            default=None,
            help=(
                "Alleen voor integreat: hoeveel dagen na de eindtijd van een seminar "
                "er nog gesynchroniseerd wordt"
            ),
        )

    def handle(self, *args, **options):
        bronnen = list(dict.fromkeys(options["bron"]))
        config = SynchronisatieConfig.van_opties(options)

        self.__waarschuw_over_ongebruikte_opties(bronnen, config)

        for bron in bronnen:
            BRONNEN[bron](config).voer_uit()

        if len(bronnen) > 1:
            self.stdout.write(self.style.SUCCESS(f"Alle bronnen klaar: {', '.join(bronnen)}"))

    def __waarschuw_over_ongebruikte_opties(
        self, bronnen: list[str], config: SynchronisatieConfig
    ) -> None:
        """Zegt het wanneer je een optie meegeeft die voor geen enkele gekozen bron telt.

        Elke syncer somt in eigen_opties op welke configvelden alleen hij
        gebruikt. Zo hoeft dit commando niets over de bronnen zelf te weten.
        """
        gebruikt = set().union(*(BRONNEN[bron].eigen_opties for bron in bronnen))
        van_anderen = set().union(*(syncer.eigen_opties for syncer in BRONNEN.values()))

        meegegeven = sorted(
            veld for veld in van_anderen - gebruikt if config.is_gezet(veld)
        )
        if not meegegeven:
            return

        namen = ", ".join("--" + veld.replace("_", "-") for veld in meegegeven)
        self.stderr.write(
            self.style.WARNING(
                f"{namen} geldt niet voor {', '.join(bronnen)} en wordt genegeerd"
            )
        )