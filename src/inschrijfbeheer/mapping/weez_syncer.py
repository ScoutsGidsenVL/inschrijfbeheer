"""Synchronisatie van Weezevent naar de Inschrijfbeheer-modellen.

Deze klasse haalt zelf niets op en mapt zelf niets. Ze bepaalt de volgorde,
stelt de context voor de mappers samen, bewaart via Synchronisatie.bewaar() en
registreert wat overgeslagen werd.
"""

import logging
import os
from datetime import timedelta

from dotenv import load_dotenv

from inschrijfbeheer.mapping.logic.mapper import MappingFout
from inschrijfbeheer.mapping.logic.weez_mappers import (
    AntwoordContext,
    InschrijvingContext,
    InschrijvingsGegevens,
    VraagContext,
    WeezAntwoordMapper,
    WeezCategorieMapper,
    WeezDeelnemerMapper,
    WeezEvenementMapper,
    WeezEvenementVraagMapper,
    WeezInschrijvingMapper,
    bepaal_inschrijvingsgegevens,
    check_verplichte_vragen,
    los_lid_op,
)
from inschrijfbeheer.mapping.logic.weez_mappers.deelnemertype_mapper import WeezDeelnemerTypeMapper
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.mapping.providers import (
    InschrijvingFilter,
    WeezClient,
    WeezEvenementProvider,
    WeezInschrijvingProvider,
    WeezTariefProvider,
)
from inschrijfbeheer.mapping.synchronisatie import (
    Synchronisatie,
    SynchronisatieActie,
    SynchronisatieConfig,
    SynchronisatieInfo,
    SynchronisatieStatus,
    SyncOnderdelen,
)
from inschrijfbeheer.models import (
    Categorie,
    Deelnemer,
    Evenement,
    EvenementVraag,
    Inschrijving,
    InschrijvingVraagAntwoord,
    WeezSynchronisatie,
    DeelnemerType
)

logger = logging.getLogger("inschrijfbeheer")
load_dotenv()

class WeezSyncer(Synchronisatie):
    """Haalt evenementen, inschrijvingen en vragen op bij Weez."""

    def __init__(
        self,
        sync_config: SynchronisatieConfig | None = None,
        client: WeezClient | None = None,
        lid_provider: LidProvider | None = None,
    ):
        # sync_config staat eerst, gelijk aan Synchronisatie.__init__, zodat
        # WeezSyncer(SynchronisatieConfig(...)) blijft werken. client en
        # lid_provider zijn er om in tests een nagemaakte bron mee te geven.
        super().__init__(sync_config)

        self.client = WeezClient() if client is None else client
        self.lid_provider = LidProvider() if lid_provider is None else lid_provider

        self.evenement_provider = WeezEvenementProvider(self.client)
        self.inschrijving_provider = WeezInschrijvingProvider(self.client)
        self.tarief_provider = WeezTariefProvider(self.client)

        # Categorie, Deelnemer, EvenementVraag en InschrijvingVraagAntwoord
        # hebben geen eigen provider: hun data zit genest in het antwoord van
        # het evenement of van de deelnemer.
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
        )
        self.vragen = SyncOnderdelen(model=EvenementVraag, mapper=WeezEvenementVraagMapper())
        self.antwoorden = SyncOnderdelen(
            model=InschrijvingVraagAntwoord, mapper=WeezAntwoordMapper()
        )
        self.deelnemertypes = SyncOnderdelen(model=DeelnemerType, mapper=WeezDeelnemerTypeMapper())

        self.tijdslimiet: str | None = None

    def synchroniseer(self) -> SynchronisatieInfo:
        """Haalt alle Weez-evenementen op en zet ze om naar Evenement-modellen."""
        self.tijdslimiet = self.__bepaal_tijdslimiet()
        WeezSynchronisatie.objects.create()  # log dat een synchronisatie is gestart
        self.info.status(SynchronisatieStatus.BEZIG)

        with self.client:
            overzicht = list(self.evenement_provider.haal_alle_op())
            if self.config.limiet is not None:
                overzicht = overzicht[: self.config.limiet]

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
            categorie = self.__bewaar_categorie(bron.get("category") or {})
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

        Args:
            evenement (Evenement | None, optional): het evenement waarvan de
                inschrijvingen gesynchroniseerd worden.

        Returns:
            SynchronisatieInfo: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
        """
        if evenement is None:
            raise ValueError("synchroniseer_inschrijvingen heeft een evenement nodig")

        tarieven = self.tarief_provider.haal_tarieven_op(evenement.id)
        deelnemertypes = {}
        for tarief in tarieven:
            deelnemertype, _ = self.bewaar(self.deelnemertypes, self.deelnemertypes.mapper.map(tarief))
            deelnemertypes[tarief["id"]] = {"prijs": tarief["prijs"], "type": deelnemertype}

        bronnen = self.inschrijving_provider.haal_alle_op(
            InschrijvingFilter(evenement_id=evenement.id, sinds=self.tijdslimiet)
        )

        for bron in bronnen:
            vragen = bron.get("answers") or []

            # Ontbreekt er een verplichte vraag, dan geldt dat voor het hele
            # formulier en dus voor alle deelnemers van dit evenement.
            if not check_verplichte_vragen(vragen):
                self.__geen_verplichte_vraag(evenement)
                break

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
                inschrijving, _ = self.bewaar(
                    self.inschrijvingen, self.inschrijvingen.mapper.map(bron, context)
                )
            except MappingFout as fout:
                logger.warning(
                    "Inschrijving overgeslagen op evenement %s: %s", evenement.id, fout
                )
                self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
                continue

            self.__synchroniseer_antwoorden(evenement, inschrijving, vragen)

        return self.info

    def synchroniseer_vragen(
        self, evenement: Evenement | None = None, inschrijving: Inschrijving | None = None
    ) -> SynchronisatieInfo:
        """Methode die alle vragen synchroniseert.
        Indien gegeven doet het dit enkel voor de vragen van een gegeven evenement.

        Args:
            evenement (Evenement | None, optional): evenement waarvoor de vragen moeten gesynchroniseerd worden. Defaults to None.
            inschrijving (Inschrijving | None, optional): nog niet ondersteund, zie hieronder. Defaults to None.

        Returns:
            SynchronisatieInfo: info over de huidige synchronisatie
        """
        if inschrijving is not None:
            raise NotImplementedError(
                "Vragen per inschrijving vereist een weez_id-veld op Inschrijving"
            )

        if evenement is None:
            raise ValueError("synchroniseer_vragen heeft een evenement nodig")

        bronnen = self.inschrijving_provider.haal_alle_op(
            InschrijvingFilter(evenement_id=evenement.id, sinds=self.tijdslimiet)
        )
        for bron in bronnen:
            vragen = bron.get("answers") or []
            for volgorde, vraag_bron in enumerate(vragen):
                self.__bewaar_vraag(evenement, volgorde, vraag_bron)

        return self.info

    def __bepaal_tijdslimiet(self) -> str | None:
        """Bepaalt vanaf welk tijdstip er opnieuw opgehaald wordt.

        Geeft None terug bij een eerste synchronisatie, zodat dan alles
        opgehaald wordt.
        """
        laatste_sync = WeezSynchronisatie.objects.order_by("-tijdstip").first()
        if laatste_sync is None:
            return None

        overlap = int(os.getenv("WEEZ_SCRAPE_OVERLAP"))
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

    def __bewaar_vraag(
        self, evenement: Evenement, volgorde: int, bron: dict
    ) -> EvenementVraag | None:
        try:
            vraag, _ = self.bewaar(
                self.vragen,
                self.vragen.mapper.map(bron, VraagContext(evenement=evenement, volgorde=volgorde)),
            )
            return vraag
        except MappingFout as fout:
            logger.warning("Vraag overgeslagen op evenement %s: %s", evenement.id, fout)
            self.info.registreer(EvenementVraag, SynchronisatieActie.OVERGESLAGEN)
            return None

    def __synchroniseer_antwoorden(
        self, evenement: Evenement, inschrijving: Inschrijving, vragen: list[dict]
    ) -> None:
        for volgorde, bron in enumerate(vragen):
            vraag = self.__bewaar_vraag(evenement, volgorde, bron)
            if vraag is None:
                self.info.registreer(
                    InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN
                )
                continue

            try:
                self.bewaar(
                    self.antwoorden,
                    self.antwoorden.mapper.map(
                        bron, AntwoordContext(vraag=vraag, inschrijving=inschrijving)
                    ),
                )
            except MappingFout as fout:
                logger.warning("Antwoord overgeslagen op vraag %s: %s", vraag.vraag, fout)
                self.info.registreer(
                    InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN
                )

    def __geen_verplichte_vraag(self, evenement: Evenement) -> None:
        self.logger.warning(
            f"Evenement {evenement.titel} ({evenement.id}) bevat één van de verplichte vragen niet"
        )
        evenement.foutboodschap = (
            "Evenement mist een verplichte vraag, inschrijvingen worden niet gesynchroniseerd"
        )
        evenement.save()