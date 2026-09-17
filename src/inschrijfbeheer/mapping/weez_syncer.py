"""Synchronisatie van Weezevent naar de Inschrijfbeheer-modellen.

Deze klasse haalt zelf niets op en mapt zelf niets. Ze bepaalt de volgorde,
stelt de context voor de mappers samen, bewaart via Synchronisatie.bewaar() en
registreert wat overgeslagen werd.

Voorlopig gaat het enkel om evenementen en inschrijvingen. Categorie en
Deelnemer blijven, want de evenement- en inschrijvingsmapper hebben ze nodig.
Tarieven, deelnemertypes, vragen en antwoorden vallen weg tot ze op de nieuwe
API opnieuw aan de beurt komen.

Aanmaken doe je met één config:

    WeezSyncer(SynchronisatieConfig(limiet=5, dry_run=True)).voer_uit()

De client, de ledenprovider en de onderdelen bouwt de syncer zelf op. In een
test geef je een nagemaakte client of ledenprovider mee als sleutelwoord.
"""

import logging
import os
from datetime import timedelta

from dotenv import load_dotenv

from inschrijfbeheer.mapping.logic.mapper import MappingFout
from inschrijfbeheer.mapping.logic.weez_mappers import (
    InschrijvingContext,
    InschrijvingsGegevens,
    WeezCategorieMapper,
    WeezDeelnemerMapper,
    WeezEvenementMapper,
    WeezInschrijvingMapper,
    bepaal_inschrijvingsgegevens,
    check_verplichte_vragen,
    los_lid_op,
)
from inschrijfbeheer.mapping.logic.weez_mappers.antwoord_mapper import AntwoordContext, WeezAntwoordMapper
from inschrijfbeheer.mapping.logic.weez_mappers.deelnemertype_mapper import WeezDeelnemerTypeMapper
from inschrijfbeheer.mapping.logic.weez_mappers.evenementvraag_mapper import VraagContext, WeezEvenementVraagMapper
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.mapping.providers import (
    InschrijvingFilter,
    WeezClient,
    WeezEvenementProvider,
    WeezInschrijvingProvider,
    WeezTariefProvider,
    TariefFilter
)
from inschrijfbeheer.mapping import (
    Synchronisatie,
    SynchronisatieActie,
    SynchronisatieConfig,
    SynchronisatieInfo,
    SynchronisatieStatus,
    SyncOnderdelen,
)
from inschrijfbeheer.mapping.providers.weez_providers.evenement_provider import EvenementFilter
from inschrijfbeheer.models import (
    Categorie,
    Deelnemer,
    Evenement,
    Inschrijving,
    WeezSynchronisatie,
)
from inschrijfbeheer.models.inschrijfbeheer_models import DeelnemerType, EvenementVraag, InschrijvingVraagAntwoord

logger = logging.getLogger("inschrijfbeheer")
load_dotenv()

STANDAARD_OVERLAP_UREN = 1


class WeezSyncer(Synchronisatie):
    """Haalt evenementen en inschrijvingen op bij Weez."""

    naam = "weez"
    eigen_opties = frozenset()

    def __init__(
        self,
        config: SynchronisatieConfig | None = None,
        *,
        client: WeezClient | None = None,
        lid_provider: LidProvider | None = None,
    ):
        super().__init__(config)

        self.client = WeezClient() if client is None else client
        self.lid_provider = LidProvider() if lid_provider is None else lid_provider

        self.evenement_provider = WeezEvenementProvider(self.client)
        self.inschrijving_provider = WeezInschrijvingProvider(self.client)
        self.tarieven_provider = WeezTariefProvider(self.client)

        self.__maak_onderdelen()

        self.tijdslimiet: str | None = None
        self.__verbindingen = 0

    def __enter__(self) -> "WeezSyncer":
        """Houdt de Weez-client open zolang je binnen het blok werkt.

        Dit telt hoe vaak je het blok binnengaat, zodat een deelsynchronisatie
        binnen een volledige synchronisatie de verbinding niet te vroeg sluit.
        """
        if self.__verbindingen == 0:
            self.client.__enter__()
        self.__verbindingen += 1
        return self

    def __exit__(self, *fout) -> bool:
        self.__verbindingen -= 1
        if self.__verbindingen == 0:
            self.client.__exit__(*fout)
        return False

    def __maak_onderdelen(self) -> None:
        """Koppelt elk model aan zijn mapper en provider.

        Dit hangt niet af van wat de gebruiker kiest, dus het staat hier en niet
        in het management command.
        """
        self.categorieen = SyncOnderdelen(
            model=Categorie, mapper=WeezCategorieMapper(), enkel_aanmaken=True
        )
        self.evenementen = SyncOnderdelen(
            model=Evenement, mapper=WeezEvenementMapper(), provider=self.evenement_provider
        )
        self.deelnemers = SyncOnderdelen(model=Deelnemer, mapper=WeezDeelnemerMapper())
        self.inschrijvingen = SyncOnderdelen(
            model=Inschrijving,
            mapper=WeezInschrijvingMapper(),
            provider=self.inschrijving_provider,
            enkel_aanmaken=False,
        )
        self.tarieven = SyncOnderdelen(
            model=DeelnemerType,
            mapper=WeezDeelnemerTypeMapper(),
            provider=self.tarieven_provider,
        )
        self.vragen = SyncOnderdelen(
            model=EvenementVraag, mapper=WeezEvenementVraagMapper(), enkel_aanmaken=False
        )
        self.antwoorden = SyncOnderdelen(
            model=InschrijvingVraagAntwoord, mapper=WeezAntwoordMapper(), enkel_aanmaken=False
        )

    def synchroniseer(self) -> SynchronisatieInfo:
        """Haalt alle Weez-evenementen op en zet ze om naar Evenement-modellen."""
        if not self.config.sync_alles:
            self.tijdslimiet = self.__bepaal_tijdslimiet()
        WeezSynchronisatie.objects.create()
        self.info.status(SynchronisatieStatus.BEZIG)

        with self:
            overzicht = list(self.evenement_provider.haal_alle_op(
                EvenementFilter(alles=self.config.sync_alles)
            ))

            for samenvatting in overzicht:
                evenement_id = samenvatting.get("id")
                if evenement_id is None:
                    logger.warning("Evenement zonder id in het overzicht, overgeslagen")
                    self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
                    continue
                self.synchroniseer_evenement(str(evenement_id), sync_inschrijvingen=True)

        self.info.status(SynchronisatieStatus.GESLAAGD)
        return self.info

    def synchroniseer_evenement(
        self, evenement_id: str, sync_inschrijvingen: bool = False
    ) -> SynchronisatieInfo:
        bron = self.evenement_provider.haal_op(evenement_id)
        if not bron:
            logger.warning("Geen details gevonden voor evenement %s", evenement_id)
            self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
            return self.info

        try:
            categorie = self.__bewaar_categorie(bron or {})
            evenement, _ = self.bewaar(
                self.evenementen, self.evenementen.mapper.map(bron, categorie)
            )
        except MappingFout as fout:
            logger.warning("Evenement %s overgeslagen: %s", evenement_id, fout)
            self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
            return self.info

        if sync_inschrijvingen:
            self.synchroniseer_inschrijvingen(evenement)

        return self.info

    def synchroniseer_inschrijvingen(self, evenement: Evenement | None = None) -> SynchronisatieInfo:
        """Synchroniseert alle deelnemers voor een bepaald evenement van Weez.

        De antwoorden op het inschrijvingsformulier worden gelezen om de
        deelnemer te kunnen samenstellen, maar voorlopig niet bewaard.

        Args:
            evenement (Evenement | None, optional): het evenement waarvan de
                inschrijvingen gesynchroniseerd worden.

        Returns:
            SynchronisatieInfo: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
        """
        if evenement is None:
            raise ValueError("synchroniseer_inschrijvingen heeft een evenement nodig")

        tarieven_bron = self.tarieven_provider.haal_alle_op(
            TariefFilter(evenement_id=evenement.id)
        )
        deelnemertypes = {}
        for tarief in tarieven_bron:
            deelnemertype, _ = self.bewaar(
                self.tarieven,
                self.tarieven.mapper.map(tarief)
            )
            deelnemertypes[deelnemertype.id] = deelnemertype


        bronnen = self.inschrijving_provider.haal_alle_op(self.__inschrijving_filter(evenement))
        vraag_index: dict[str, EvenementVraag] | None = None

        for bron in bronnen:
            vragen = bron.get("form") or []

            alle_verplichte_vragen, rest = check_verplichte_vragen(vragen)
            if not alle_verplichte_vragen:
                self.__geen_verplichte_vraag(evenement, rest)
                break

            if vraag_index is None:
                vraag_index = self.__bewaar_vragen(evenement, vragen)

            gegevens = bepaal_inschrijvingsgegevens(vragen)
            if gegevens is None:
                logger.warning(
                    "Deelnemer met onvolledige ledengegevens op evenement %s", evenement.id
                )
                self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
                continue

            deelnemer = self.__bewaar_deelnemer(gegevens)
            if deelnemer is None:
                self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
                continue

            try:
                context = InschrijvingContext(
                    evenement=evenement, deelnemer=deelnemer, deelnemertypes=deelnemertypes
                )
                inschrijving, _ = self.bewaar(self.inschrijvingen, self.inschrijvingen.mapper.map(bron, context))


            except MappingFout as fout:
                logger.warning(
                    "Inschrijving overgeslagen op evenement %s: %s", evenement.id, fout
                )
                self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
                continue

            self.__bewaar_antwoorden(inschrijving, vragen, vraag_index)

        return self.info

    def synchroniseer_vragen(self, evenement=None, inschrijving=None):
        return super().synchroniseer_vragen(evenement, inschrijving)

    def __inschrijving_filter(self, evenement: Evenement) -> InschrijvingFilter:
        """Stelt het filter samen waarmee je inschrijvingen ophaalt."""
        return InschrijvingFilter(
            evenement_id=evenement.id,
            sinds=self.tijdslimiet,
            sync_alles=self.config.sync_alles,
        )

    def __bepaal_tijdslimiet(self) -> str | None:
        """Bepaalt vanaf welk tijdstip er opnieuw opgehaald wordt.

        Geeft None terug bij een eerste synchronisatie, zodat dan alles
        opgehaald wordt.
        """
        laatste_sync = WeezSynchronisatie.objects.order_by("-tijdstip").first()
        if laatste_sync is None:
            return None

        overlap = int(os.getenv("WEEZ_SCRAPE_OVERLAP") or STANDAARD_OVERLAP_UREN)
        return (laatste_sync.tijdstip - timedelta(hours=overlap)).strftime("%Y-%m-%d %H:%M:%S")

    def __bewaar_categorie(self, bron: dict) -> Categorie | None:
        if not bron:
            return None
        try:
            categorie, _ = self.bewaar(self.categorieen, self.categorieen.mapper.map(bron, None))
            return categorie
        except MappingFout as fout:
            logger.warning("Categorie overgeslagen: %s", fout)
            self.info.registreer(Categorie, SynchronisatieActie.OVERGESLAGEN)
            return None

    def __bewaar_deelnemer(self, gegevens: InschrijvingsGegevens) -> Deelnemer | None:
        resultaat = los_lid_op(self.lid_provider, gegevens)
        if resultaat.foutboodschap:
            logger.warning("Deelnemer met foutboodschap: %s", resultaat.foutboodschap)

        try:
            deelnemer, _ = self.bewaar(
                self.deelnemers, self.deelnemers.mapper.map(gegevens, resultaat)
            )
            return deelnemer
        except MappingFout as fout:
            logger.warning("Deelnemer overgeslagen: %s", fout)
            self.info.registreer(Deelnemer, SynchronisatieActie.OVERGESLAGEN)
            return None

    def __geen_verplichte_vraag(self, evenement: Evenement, rest: set) -> None:
        logger.warning(
            "Evenement %s (%s) mist volgende verplichte vragen: %s",
            evenement.titel,
            evenement.id,
            ", ".join(rest),
        )
        evenement.foutboodschap = (
            f"Evenement mist volgende verplichte vragen: {', '.join(rest)}, "
            "inschrijvingen worden niet gesynchroniseerd"
        )
        evenement.save()

    def __bewaar_vragen(self, evenement: Evenement, vragen: list[dict]) -> dict[str, EvenementVraag]:
        """Bewaart het formulier van het evenement en geeft de vragen terug per Weez-id."""
        index: dict[str, EvenementVraag] = {}
        for volgorde, bron in enumerate(vragen):
            try:
                vraag, _ = self.bewaar(
                    self.vragen,
                    self.vragen.mapper.map(bron, VraagContext(evenement=evenement, volgorde=volgorde)),
                )
            except MappingFout as fout:
                logger.warning("Vraag overgeslagen op evenement %s: %s", evenement.id, fout)
                self.info.registreer(EvenementVraag, SynchronisatieActie.OVERGESLAGEN)
                continue
            index[str(bron.get("weez_id"))] = vraag
        return index

    def __bewaar_antwoorden(
        self, inschrijving: Inschrijving, vragen: list[dict], vraag_index: dict[str, EvenementVraag]
    ) -> None:
        for bron in vragen:
            vraag = vraag_index.get(str(bron.get("weez_id")))
            if vraag is None:
                logger.warning("Antwoord zonder gekende vraag op inschrijving %s", inschrijving.id)
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN)
                continue
            try:
                self.bewaar(
                    self.antwoorden,
                    self.antwoorden.mapper.map(bron, AntwoordContext(inschrijving=inschrijving, vraag=vraag)),
                )
            except MappingFout as fout:
                logger.warning("Antwoord overgeslagen op inschrijving %s: %s", inschrijving.id, fout)
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN)