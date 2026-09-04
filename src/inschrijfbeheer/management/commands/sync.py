"""Management command dat een synchronisatie start, voor Weez of Integreat.

De bestandsnaam bepaalt de naam van het commando:
    inschrijfbeheer/management/commands/sync.py -> manage.py sync

    manage.py sync weez
    manage.py sync integreat --alles
    manage.py sync weez integreat --dry-run
"""

import logging
from typing import Callable

from django.core.management.base import BaseCommand
from django.db import transaction

from inschrijfbeheer.mapping.providers.data_provider import IntegreatFilter
from inschrijfbeheer.mapping.providers.integreat_providers import (
    IntegreatParticipantTypeProvider,
    IntegreatRegistrationfreefieldProvider,
    IntegreatRegistrationProvider,
    IntegreatSeminarFreeFieldProvider,
    IntegreatSeminarFreeFieldTypeProvider,
    IntegreatSeminarProvider,
)
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.mapping.integreat_syncer import IntegreatProviders, IntegreatSyncer
from inschrijfbeheer.mapping.synchronisatie import Synchronisatie, SynchronisatieConfig
from inschrijfbeheer.mapping.weez_syncer import WeezSyncer

logger = logging.getLogger("inschrijfbeheer")

INTEGREAT_OPTIES = ("alles", "terugblik_dagen")


def maak_integreat_providers() -> IntegreatProviders:
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


def maak_weez_syncer(opties: dict) -> Synchronisatie:
    return WeezSyncer(SynchronisatieConfig(limiet=opties["limiet"]))


def maak_integreat_syncer(opties: dict) -> Synchronisatie:
    filter_velden = {"sync_alles": opties["alles"], "limiet": opties["limiet"]}
    if opties["terugblik_dagen"] is not None:
        filter_velden["terugblik_dagen"] = opties["terugblik_dagen"]

    return IntegreatSyncer(
        providers=maak_integreat_providers(),
        sync_config=SynchronisatieConfig(limiet=opties["limiet"]),
        bron_filter=IntegreatFilter(**filter_velden),
    )


# Databronnen, indien er ooit één bijkomt een regel toevoegen
BRONNEN: dict[str, Callable[[dict], Synchronisatie]] = {
    "weez": maak_weez_syncer,
    "integreat": maak_integreat_syncer,
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
            help="Alleen voor integreat: negeert het terugblikvenster en haalt ook oude seminars op",
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
        self.__waarschuw_over_ongebruikte_opties(bronnen, options)

        for bron in bronnen:
            self.__synchroniseer(bron, options)

        if len(bronnen) > 1:
            self.stdout.write(self.style.SUCCESS(f"Alle bronnen klaar: {', '.join(bronnen)}"))

    def __synchroniseer(self, bron: str, opties: dict) -> None:
        dry_run = opties["dry_run"]
        aanduiding = f"[{bron.upper()} SYNC]"

        syncer = BRONNEN[bron](opties)

        # transactie per bron zodat falen van één bron geen effect heeft op de rest
        with transaction.atomic():
            syncer.synchroniseer()
            syncer.log_info()

            if dry_run:
                transaction.set_rollback(True)
                logger.info(
                    f"{aanduiding} Dry-run: alle wijzigingen teruggedraaid, niets opgeslagen."
                )


    def __waarschuw_over_ongebruikte_opties(self, bronnen: list[str], opties: dict) -> None:
        """Zegt het wanneer je een Integreat-optie meegeeft zonder Integreat te synchroniseren."""
        if "integreat" in bronnen:
            return

        meegegeven = [naam for naam in INTEGREAT_OPTIES if opties.get(naam)]
        if meegegeven:
            namen = ", ".join("--" + naam.replace("_", "-") for naam in meegegeven)
            self.stderr.write(
                self.style.WARNING(f"{namen} geldt enkel voor integreat en wordt genegeerd")
            )