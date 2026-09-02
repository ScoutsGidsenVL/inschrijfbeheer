"""Synchronisatie van de Integreat-databank naar de nieuwe modellen.

Dit is de tegenhanger van de oude laad_*-functies. Het ophalen zit in de
providers, het omzetten in de mappers, en deze klasse bepaalt enkel de
volgorde, stelt de context samen en bewaart via Synchronisatie.bewaar().

De providers krijg je via IntegreatProviders binnen, zodat deze klasse niet
hoeft te weten hoe jouw providerklassen heten. Twee verwachtingen daarover:
de seminarprovider levert haal_op() op de seminarcode (niet op de oid), en
de ledenprovider levert haal_op() op het lidnummer.
"""

import logging
from dataclasses import dataclass
from typing import Any

from inschrijfbeheer.mapping.logic.mapper import MappingFout
from inschrijfbeheer.mapping.logic.integreat_mappers.integreat_mapper import (
    AntwoordContext,
    EvenementContext,
    InschrijvingContext,
    IntegreatAntwoordMapper,
    IntegreatCategorieMapper,
    IntegreatDeelnemerMapper,
    IntegreatDeelnemerTypeMapper,
    IntegreatEvenementMapper,
    IntegreatEvenementVraagMapper,
    IntegreatInschrijvingMapper,
    IntegreatStatusMapper,
    IntegreatVraagTypeMapper,
    VraagContext,
    normaliseer_code,
)
from inschrijfbeheer.mapping.providers.data_provider import LijstProvider
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
    DeelnemerType,
    Evenement,
    EvenementStatus,
    EvenementVraag,
    EvenementVraagType,
    Inschrijving,
    InschrijvingVraagAntwoord,
)

logger = logging.getLogger("inschrijfbeheer")


@dataclass
class IntegreatProviders:
    """De providers op de databank "integreat", door de aanroeper samengesteld."""

    seminars: Any
    deelnemertypes: LijstProvider
    vraagtypes: LijstProvider
    vragen: LijstProvider
    registraties: LijstProvider
    antwoorden: LijstProvider
    leden: LijstProvider


class IntegreatSyncer(Synchronisatie):
    """Zet de oude Integreat-records om naar de nieuwe modellen."""

    def __init__(
        self,
        providers: IntegreatProviders,
        sync_config: SynchronisatieConfig | None = None,
        bron_filter: Any = None,
    ):
        super().__init__(sync_config)
        self.providers = providers
        self.bron_filter = bron_filter

        self.statussen = SyncOnderdelen(
            model=EvenementStatus, mapper=IntegreatStatusMapper(), enkel_aanmaken=True
        )
        self.categorieen = SyncOnderdelen(model=Categorie, mapper=IntegreatCategorieMapper())
        self.evenementen = SyncOnderdelen(
            model=Evenement, mapper=IntegreatEvenementMapper(), provider=providers.seminars
        )
        self.deelnemertypes = SyncOnderdelen(
            model=DeelnemerType,
            mapper=IntegreatDeelnemerTypeMapper(),
            provider=providers.deelnemertypes,
        )
        self.deelnemers = SyncOnderdelen(model=Deelnemer, mapper=IntegreatDeelnemerMapper())
        self.inschrijvingen = SyncOnderdelen(
            model=Inschrijving,
            mapper=IntegreatInschrijvingMapper(),
            provider=providers.registraties,
        )
        self.vraagtypes = SyncOnderdelen(
            model=EvenementVraagType,
            mapper=IntegreatVraagTypeMapper(),
            provider=providers.vraagtypes,
        )
        self.vragen = SyncOnderdelen(
            model=EvenementVraag, mapper=IntegreatEvenementVraagMapper(), provider=providers.vragen
        )
        self.antwoorden = SyncOnderdelen(
            model=InschrijvingVraagAntwoord,
            mapper=IntegreatAntwoordMapper(),
            provider=providers.antwoorden,
        )

    def synchroniseer(self) -> SynchronisatieInfo:
        """Voert de volledige migratie uit, in de volgorde die de relaties vragen."""
        self.info.status(SynchronisatieStatus.BEZIG)

        self.__synchroniseer_vraagtypes()
        self.__synchroniseer_deelnemertypes()
        self.__synchroniseer_seminars()
        self.synchroniseer_inschrijvingen()
        self.synchroniseer_vragen()
        self.__synchroniseer_antwoorden()

        self.info.status(SynchronisatieStatus.GESLAAGD)
        return self.info

    def synchroniseer_evenement(
        self, evenement_id: str, sync_inschrijvingen: bool = False
    ) -> SynchronisatieInfo:
        """Synchroniseert één seminar, opgezocht via zijn code."""
        seminar = self.providers.seminars.haal_op(evenement_id)
        if seminar is None:
            logger.warning("Geen seminar gevonden met code %s", evenement_id)
            self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
            return self.info

        evenement = self.__bewaar_seminar(seminar)
        if evenement is not None and sync_inschrijvingen:
            self.synchroniseer_inschrijvingen(evenement)

        return self.info

    def synchroniseer_inschrijvingen(self, evenement: Evenement | None = None) -> SynchronisatieInfo:
        """Synchroniseert de registraties, eventueel enkel die van één evenement."""
        for registratie in self.providers.registraties.haal_alle_op(self.bron_filter):
            if evenement is not None and self.__seminar_code(registratie) != evenement.id:
                continue

            self.__bewaar_registratie(registratie, evenement)

        return self.info

    def synchroniseer_vragen(
        self, evenement: Evenement | None = None, inschrijving: Inschrijving | None = None
    ) -> SynchronisatieInfo:
        """Synchroniseert de vrije velden van de seminars naar EvenementVraag.

        De antwoorden erop zijn een eigen stap, want die hangen zowel van de
        vraag als van de inschrijving af.
        """
        if inschrijving is not None:
            raise NotImplementedError(
                "Vragen per inschrijving heeft geen betekenis in Integreat, "
                "een vraag hoort bij een seminar en niet bij een registratie"
            )

        for vrij_veld in self.providers.vragen.haal_alle_op(self.bron_filter):
            if evenement is not None and normaliseer_code(
                getattr(vrij_veld.seminar, "code", None)
            ) != evenement.id:
                continue

            self.__bewaar_vrij_veld(vrij_veld)

        return self.info

    def __synchroniseer_vraagtypes(self) -> None:
        for bron in self.providers.vraagtypes.haal_alle_op(self.bron_filter):
            try:
                self.bewaar(self.vraagtypes, self.vraagtypes.mapper.map(bron, None))
            except MappingFout as fout:
                logger.warning("Vraagtype overgeslagen: %s", fout)
                self.info.registreer(EvenementVraagType, SynchronisatieActie.OVERGESLAGEN)

    def __synchroniseer_deelnemertypes(self) -> None:
        for bron in self.providers.deelnemertypes.haal_alle_op(self.bron_filter):
            try:
                self.bewaar(self.deelnemertypes, self.deelnemertypes.mapper.map(bron, None))
            except MappingFout as fout:
                logger.warning("Deelnemertype overgeslagen: %s", fout)
                self.info.registreer(DeelnemerType, SynchronisatieActie.OVERGESLAGEN)

    def __synchroniseer_seminars(self) -> None:
        for seminar in self.providers.seminars.haal_alle_op(self.bron_filter):
            self.__bewaar_seminar(seminar)

    def __synchroniseer_antwoorden(self) -> None:
        for bron in self.providers.antwoorden.haal_alle_op(self.bron_filter):
            vraag_oid = getattr(bron.field, "oid", None)
            registratie_oid = getattr(bron.registration, "oid", None)
            if vraag_oid is None or registratie_oid is None:
                logger.warning("Antwoord %s zonder vraag of registratie", bron.oid)
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN)
                continue

            vraag = EvenementVraag.objects.filter(id=vraag_oid).first()
            inschrijving = Inschrijving.objects.filter(id=registratie_oid).first()
            if vraag is None or inschrijving is None:
                logger.warning(
                    "Antwoord %s overgeslagen: vraag of inschrijving nog niet aanwezig", bron.oid
                )
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN)
                continue

            try:
                self.bewaar(
                    self.antwoorden,
                    self.antwoorden.mapper.map(
                        bron, AntwoordContext(vraag=vraag, inschrijving=inschrijving)
                    ),
                )
            except MappingFout as fout:
                logger.warning("Antwoord %s overgeslagen: %s", bron.oid, fout)
                self.info.registreer(InschrijvingVraagAntwoord, SynchronisatieActie.OVERGESLAGEN)

    def __bewaar_seminar(self, seminar) -> Evenement | None:
        try:
            status, _ = self.bewaar(self.statussen, self.statussen.mapper.map(seminar.status, None))
            categorie, _ = self.bewaar(
                self.categorieen, self.categorieen.mapper.map(seminar.type, None)
            )
            evenement, _ = self.bewaar(
                self.evenementen,
                self.evenementen.mapper.map(
                    seminar, EvenementContext(status=status, categorie=categorie)
                ),
            )
            return evenement
        except MappingFout as fout:
            logger.warning("Seminar %s overgeslagen: %s", seminar.oid, fout)
            self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
            return None

    def __bewaar_registratie(self, registratie, evenement: Evenement | None) -> None:
        code = self.__seminar_code(registratie)
        type_oid = getattr(registratie.deelnemers_type, "oid", None)
        if not code or type_oid is None or registratie.deelnemer is None:
            logger.warning(
                "Registratie %s overgeslagen: seminar, deelnemerstype of deelnemer ontbreekt",
                registratie.oid,
            )
            self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
            return

        doel_evenement = evenement or Evenement.objects.filter(id=code).first()
        deelnemertype = DeelnemerType.objects.filter(id=str(type_oid)).first()
        if doel_evenement is None or deelnemertype is None:
            logger.warning(
                "Registratie %s overgeslagen: evenement of deelnemertype nog niet aanwezig",
                registratie.oid,
            )
            self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
            return

        deelnemer = self.__bewaar_deelnemer(registratie.deelnemer)
        if deelnemer is None:
            self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
            return

        try:
            self.bewaar(
                self.inschrijvingen,
                self.inschrijvingen.mapper.map(
                    registratie,
                    InschrijvingContext(
                        evenement=doel_evenement,
                        deelnemer=deelnemer,
                        deelnemertype=deelnemertype,
                    ),
                ),
            )
        except MappingFout as fout:
            logger.warning("Registratie %s overgeslagen: %s", registratie.oid, fout)
            self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)

    def __bewaar_deelnemer(self, bron) -> Deelnemer | None:
        lidnummer = (bron.lid_id or "").strip()
        if not lidnummer:
            logger.warning("Deelnemer %s zonder lidnummer", getattr(bron, "oid", "?"))
            self.info.registreer(Deelnemer, SynchronisatieActie.OVERGESLAGEN)
            return None

        # De ledenopzoeking staat hier en niet in de mapper, zodat map() geen
        # netwerkaanroep doet en dus zonder SOAP te testen valt.
        lidgegevens = self.providers.leden.haal_op(lidnummer)
        try:
            deelnemer, _ = self.bewaar(
                self.deelnemers, self.deelnemers.mapper.map(bron, lidgegevens)
            )
            return deelnemer
        except MappingFout as fout:
            logger.warning("Deelnemer overgeslagen: %s", fout)
            self.info.registreer(Deelnemer, SynchronisatieActie.OVERGESLAGEN)
            return None

    def __bewaar_vrij_veld(self, vrij_veld) -> None:
        code = normaliseer_code(getattr(vrij_veld.seminar, "code", None))
        type_code = normaliseer_code(getattr(vrij_veld.type, "code", None))

        evenement = Evenement.objects.filter(id=code).first()
        vraagtype = EvenementVraagType.objects.filter(naam=type_code).first()
        if evenement is None or vraagtype is None:
            logger.warning(
                "Vrij veld %s overgeslagen: evenement %r of vraagtype %r niet gevonden",
                vrij_veld.oid,
                code,
                type_code,
            )
            self.info.registreer(EvenementVraag, SynchronisatieActie.OVERGESLAGEN)
            return

        try:
            self.bewaar(
                self.vragen,
                self.vragen.mapper.map(
                    vrij_veld, VraagContext(evenement=evenement, type=vraagtype)
                ),
            )
        except MappingFout as fout:
            logger.warning("Vrij veld %s overgeslagen: %s", vrij_veld.oid, fout)
            self.info.registreer(EvenementVraag, SynchronisatieActie.OVERGESLAGEN)

    @staticmethod
    def __seminar_code(registratie) -> str:
        return normaliseer_code(getattr(registratie.seminar, "code", None))