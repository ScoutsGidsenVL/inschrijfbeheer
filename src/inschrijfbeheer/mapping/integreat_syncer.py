"""Synchronisatie van de Integreat-databank naar de nieuwe modellen.

Dit is de tegenhanger van de oude laad_*-functies. Het ophalen zit in de
providers, het omzetten in de mappers, en deze klasse bepaalt enkel de
volgorde, stelt de context samen en bewaart via Synchronisatie.bewaar().

De syncer werkt per evenement. synchroniseer() haalt eerst de types op die los
van een evenement staan, loopt daarna over de evenementen die recent genoeg
zijn, en haalt binnen die lus enkel de vragen, inschrijvingen en antwoorden op
die bij het evenement in kwestie horen.

Aanmaken doe je met één config:

    IntegreatSyncer(SynchronisatieConfig(terugblik_dagen=30)).voer_uit()

De providers en het bronfilter bouwt de syncer dan zelf op. In een test geef je
nagemaakte providers mee als sleutelwoord:

    IntegreatSyncer(config, providers=IntegreatProviders(seminars=..., ...))

Twee verwachtingen over die providers: de seminarprovider levert haal_op() op
de seminarcode (niet op de oid), en de ledenprovider levert haal_op() op het
lidnummer.
"""

import logging
from dataclasses import dataclass
from typing import Any

from inschrijfbeheer.mapping.logic.mapper import MappingFout
from inschrijfbeheer.mapping.logic.integreat_mappers import (
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
    IntegreatVraagTypeMapper,
    VraagContext,
    normaliseer_code,
)
from inschrijfbeheer.mapping.providers.data_provider import EvenementFilter, IntegreatFilter, LijstProvider
from inschrijfbeheer.mapping.providers.integreat_providers import (
    IntegreatParticipantTypeProvider,
    IntegreatRegistrationfreefieldProvider,
    IntegreatRegistrationProvider,
    IntegreatSeminarFreeFieldProvider,
    IntegreatSeminarFreeFieldTypeProvider,
    IntegreatSeminarProvider,
)
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.mapping import (
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
    EvenementVraag,
    EvenementVraagType,
    Inschrijving,
    InschrijvingVraagAntwoord,
)

logger = logging.getLogger("inschrijfbeheer")


@dataclass
class IntegreatProviders:
    """De providers op de databank "integreat"."""

    seminars: Any
    deelnemertypes: LijstProvider
    vraagtypes: LijstProvider
    vragen: LijstProvider
    registraties: LijstProvider
    antwoorden: LijstProvider
    leden: LijstProvider

    @classmethod
    def standaard(cls) -> "IntegreatProviders":
        """De echte providers, die IntegreatSyncer gebruikt als je niets meegeeft.

        Ze staan in een aparte methode zodat je in een test dezelfde syncer met
        nagemaakte providers kan gebruiken.
        """
        return cls(
            seminars=IntegreatSeminarProvider(),
            deelnemertypes=IntegreatParticipantTypeProvider(),
            vraagtypes=IntegreatSeminarFreeFieldTypeProvider(),
            vragen=IntegreatSeminarFreeFieldProvider(),
            registraties=IntegreatRegistrationProvider(),
            antwoorden=IntegreatRegistrationfreefieldProvider(),
            leden=LidProvider(),
        )


class IntegreatSyncer(Synchronisatie):
    """Zet de oude Integreat-records om naar de nieuwe modellen."""

    naam = "integreat"
    eigen_opties = frozenset({"terugblik_dagen"})

    def __init__(
        self,
        config: SynchronisatieConfig | None = None,
        *,
        providers: IntegreatProviders | None = None,
        bron_filter: IntegreatFilter | None = None,
    ):
        super().__init__(config)
        self.providers = IntegreatProviders.standaard() if providers is None else providers
        self.bron_filter = self.__maak_filter() if bron_filter is None else bron_filter

        self.__maak_onderdelen()

    def __maak_filter(self) -> IntegreatFilter:
        """Vertaalt de config naar het filter waarmee de providers ophalen."""
        velden: dict[str, Any] = {
            "sync_alles": self.config.sync_alles,
        }
        if self.config.terugblik_dagen is not None:
            velden["terugblik_dagen"] = self.config.terugblik_dagen

        return IntegreatFilter(**velden)

    def __maak_onderdelen(self) -> None:
        """Koppelt elk model aan zijn mapper en provider.

        Dit hangt niet af van wat de gebruiker kiest, dus het staat hier en niet
        in het management command.
        """
        providers = self.providers
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
        """Voert de volledige migratie uit, evenement per evenement.

        De vraagtypes en deelnemertypes hangen aan geen enkel evenement vast,
        dus die gaan vooraf. Daarna loopt de syncer over de seminars die binnen
        de terugblik vallen. Alles wat aan een evenement hangt, haalt hij
        binnen die lus op, zodat er niets binnenkomt van een evenement dat te
        oud is.
        """
        self.info.status(SynchronisatieStatus.BEZIG)
        # try:
        self.__synchroniseer_vraagtypes()
        self.__synchroniseer_deelnemertypes()

        for seminar in self.__haal_seminars_op():
            self.__synchroniseer_seminar(seminar, met_inschrijvingen=True)

        self.info.status(SynchronisatieStatus.GESLAAGD)
        # except Exception as e:
        # logger.error(f"Error opgeworpen bij synchronisatie: {e}")
        # self.info.status(SynchronisatieStatus.FOUTIEF)
        # finally:
        return self.info

    def synchroniseer_evenement(
        self, evenement_id: str, sync_inschrijvingen: bool = False
    ) -> SynchronisatieInfo:
        """Synchroniseert één seminar, opgezocht via zijn code.

        De vragen horen bij het seminar en gaan dus altijd mee. De registraties
        en hun antwoorden alleen als je erom vraagt. De leeftijd van het
        evenement speelt hier geen rol: vraag je expliciet om dit evenement,
        dan krijg je het.
        """
        code = normaliseer_code(evenement_id)
        seminar = self.providers.seminars.haal_op(code)
        if seminar is None:
            logger.warning("Geen seminar gevonden met code %s", code)
            self.info.registreer(Evenement, SynchronisatieActie.OVERGESLAGEN)
            return self.info

        self.__synchroniseer_seminar(seminar, met_inschrijvingen=sync_inschrijvingen)
        return self.info

    def __synchroniseer_seminar(self, seminar, *, met_inschrijvingen: bool) -> Evenement | None:
        """Bewaart het seminar en alles wat eraan hangt.

        Dit is het hart van de lus in synchroniseer(), en meteen ook de weg die
        synchroniseer_evenement() volgt voor één seminar.
        """
        evenement = self.__bewaar_seminar(seminar)
        if evenement is None:
            return None

        self.synchroniseer_vragen(evenement)
        if met_inschrijvingen:
            self.synchroniseer_inschrijvingen(evenement)
            self.synchroniseer_antwoorden(evenement)

        return evenement

    def synchroniseer_inschrijvingen(self, evenement: Evenement) -> SynchronisatieInfo:
        """Synchroniseert de registraties van één evenement."""
        for registratie in self.__haal_registraties_op(evenement):
            if self.__seminar_code(registratie) != evenement.id:
                continue

            self.__bewaar_registratie(registratie, evenement)

        return self.info

    def synchroniseer_vragen(
        self, evenement: Evenement, inschrijving: Inschrijving | None = None
    ) -> SynchronisatieInfo:
        """Synchroniseert de vrije velden van één seminar naar EvenementVraag.

        De antwoorden erop zijn een eigen stap, want die hangen zowel van de
        vraag als van de inschrijving af.
        """
        if inschrijving is not None:
            raise NotImplementedError(
                "Vragen per inschrijving heeft geen betekenis in Integreat, "
                "een vraag hoort bij een seminar en niet bij een registratie"
            )

        for vrij_veld in self.__haal_vragen_op(evenement):
            if normaliseer_code(getattr(vrij_veld.seminar, "code", None)) != evenement.id:
                continue

            self.__bewaar_vrij_veld(vrij_veld, evenement)

        return self.info

    def synchroniseer_antwoorden(self, evenement: Evenement) -> SynchronisatieInfo:
        """Koppelt de antwoorden van één evenement aan hun vraag en inschrijving.

        Dit is een eigen stap, want een antwoord hangt zowel van een vraag als
        van een inschrijving af. Beide moeten er dus al staan.
        """
        for bron in self.__haal_antwoorden_op(evenement):
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

        return self.info

    def __haal_seminars_op(self):
        """De seminars waarover synchroniseer() loopt.

        TODO: hier komt de leeftijdscontrole. Enkel seminars jonger dan
        config.terugblik_dagen mogen hier nog uit komen, de rest valt weg voor
        er ook maar één inschrijving of vraag opgehaald wordt.
        """
        return self.providers.seminars.haal_alle_op(self.bron_filter)

    def __haal_registraties_op(self, evenement: Evenement):
        """De registraties van één evenement.
        """
        filter = EvenementFilter(evenement_id=evenement.id)

        return self.__voor_seminar(
            self.providers.registraties.haal_alle_op(filter=filter), "seminar__code", evenement
        )

    def __haal_vragen_op(self, evenement: Evenement):
        """De vrije velden van één evenement.
        """
        filter = EvenementFilter(evenement_id=evenement.id)
        return self.__voor_seminar(
            self.providers.vragen.haal_alle_op(filter=filter), "seminar__code", evenement
        )

    def __haal_antwoorden_op(self, evenement: Evenement):
        """De antwoorden van één evenement.
        """
        filter = EvenementFilter(evenement_id=evenement.id)
        return self.__voor_seminar(
            self.providers.antwoorden.haal_alle_op(filter=filter),
            "registration__seminar__code",
            evenement,
        )

    @staticmethod
    def __voor_seminar(records, pad: str, evenement: Evenement):
        """Beperkt de records tot één seminar, in de databank zelf.

        De code staat met opvulruimte in de bron, dus contains doet het grove
        werk en de exacte vergelijking gebeurt daarna in Python.
        """
        return records.filter(**{f"{pad}__contains": evenement.id})

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

    def __bewaar_registratie(self, registratie, evenement: Evenement) -> None:
        code = self.__seminar_code(registratie)
        if not code or registratie.deelnemers_type is None or registratie.deelnemer is None:
            logger.warning(
                "Registratie %s overgeslagen: seminar, deelnemerstype of deelnemer ontbreekt",
                registratie.oid,
            )
            self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)
            return

        deelnemertype = self.__deelnemertype(registratie.deelnemers_type)
        if deelnemertype is None:
            logger.warning(
                "Registratie %s overgeslagen: deelnemertype nog niet aanwezig", registratie.oid
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
                        evenement=evenement,
                        deelnemer=deelnemer,
                        deelnemertype=deelnemertype,
                    ),
                ),
            )
        except MappingFout as fout:
            logger.warning("Registratie %s overgeslagen: %s", registratie.oid, fout)
            self.info.registreer(Inschrijving, SynchronisatieActie.OVERGESLAGEN)

    def __bewaar_vrij_veld(self, vrij_veld, evenement: Evenement) -> None:
        vraagtype = self.__vraagtype(vrij_veld.type)
        if vraagtype is None:
            logger.warning("Vrij veld %s overgeslagen: vraagtype niet gevonden", vrij_veld.oid)
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

    def __bewaar_deelnemer(self, bron) -> Deelnemer | None:
        lidnummer = (bron.lid_id or "").strip()
        if not lidnummer:
            logger.warning("Deelnemer %s zonder lidnummer", getattr(bron, "oid", "?"))
            self.info.registreer(Deelnemer, SynchronisatieActie.OVERGESLAGEN)
            return None

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


    def __deelnemertype(self, bron) -> DeelnemerType | None:
        """Zoekt het deelnemerstype, en maakt het aan als het er nog niet staat.

        Bij een volledige synchronisatie staan de types er al. Synchroniseer je
        één evenement, dan hangt het type aan de registratie, dus is er geen
        aparte ophaalstap voor nodig.
        """
        type_oid = getattr(bron, "oid", None)
        if type_oid is None:
            return None

        bestaand = DeelnemerType.objects.filter(id=str(type_oid)).first()
        if bestaand is not None:
            return bestaand

        try:
            deelnemertype, _ = self.bewaar(
                self.deelnemertypes, self.deelnemertypes.mapper.map(bron, None)
            )
            return deelnemertype
        except MappingFout as fout:
            logger.warning("Deelnemertype %s overgeslagen: %s", type_oid, fout)
            self.info.registreer(DeelnemerType, SynchronisatieActie.OVERGESLAGEN)
            return None

    def __vraagtype(self, bron) -> EvenementVraagType | None:
        """Zoekt het vraagtype, en maakt het aan als het er nog niet staat."""
        type_code = normaliseer_code(getattr(bron, "code", None))
        if not type_code:
            return None

        bestaand = EvenementVraagType.objects.filter(naam=type_code).first()
        if bestaand is not None:
            return bestaand

        try:
            vraagtype, _ = self.bewaar(self.vraagtypes, self.vraagtypes.mapper.map(bron, None))
            return vraagtype
        except MappingFout as fout:
            logger.warning("Vraagtype %s overgeslagen: %s", type_code, fout)
            self.info.registreer(EvenementVraagType, SynchronisatieActie.OVERGESLAGEN)
            return None

    @staticmethod
    def __seminar_code(registratie) -> str:
        return normaliseer_code(getattr(registratie.seminar, "code", None))