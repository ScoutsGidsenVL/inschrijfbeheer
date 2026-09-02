"""Mappers van de Integreat-databank naar de nieuwe Inschrijfbeheer-modellen.

De brondata is hier geen JSON maar een modelinstantie uit de databank
"integreat", dus T is telkens een Integreat-model. Verder geldt hetzelfde als
bij de Weez-mappers: geen databankwerk, geen tellers, geen netwerkaanroepen,
en wat niet omzetbaar is wordt een MappingFout.

De get_or_create- en update_or_create-aanroepen uit de oude laad_*-functies
zitten nu in de sleutels en velden van Doelgegevens. Synchronisatie.bewaar()
voert ze uit en telt wat er gebeurde.
"""

from dataclasses import dataclass
from typing import Any

from django.utils import timezone

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
    IntegreatParticipant,
    IntegreatParticipantType,
    IntegreatRegistration,
    IntegreatRegistrationfreefield,
    IntegreatSeminar,
    IntegreatSeminarFreeField,
    IntegreatSeminarFreeFieldType,
    IntegreatSeminarStatus,
    IntegreatSeminarType,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout


def tekst(waarde: str | None) -> str:
    """Maakt witruimte en None onschadelijk.
    """
    return (waarde or "").strip()


def normaliseer_code(code: str | None) -> str:
    """De code van een seminar of seminartype is de sleutel in de nieuwe databank.
    """
    return tekst(code)


class IntegreatStatusMapper(Mapper[IntegreatSeminarStatus, None, EvenementStatus]):
    """EvenementStatus, ontdubbeld op beschrijving.
    """

    def map(self, bron: IntegreatSeminarStatus, context: None = None) -> Doelgegevens[EvenementStatus]:
        return Doelgegevens(sleutels={"beschrijving": tekst(bron.beschrijving)})


class IntegreatCategorieMapper(Mapper[IntegreatSeminarType, None, Categorie]):
    """Categorie, met de code van het seminartype als sleutel.
    """

    def map(self, bron: IntegreatSeminarType, context: None = None) -> Doelgegevens[Categorie]:
        code = normaliseer_code(bron.code)
        if not code:
            raise MappingFout("seminartype zonder code")

        naam = tekst(bron.naam)
        return Doelgegevens(
            sleutels={"id": code},
            velden={
                "naam": naam,
                "alt_naam": naam
            }
        )


@dataclass(frozen=True)
class EvenementContext:
    """De status en de categorie zijn al bewaard voor het evenement gemapt wordt."""

    status: EvenementStatus
    categorie: Categorie


class IntegreatEvenementMapper(Mapper[IntegreatSeminar, EvenementContext, Evenement]):
    """Evenement uit een seminar.
    """

    def map(self, bron: IntegreatSeminar, context: EvenementContext) -> Doelgegevens[Evenement]:
        code = normaliseer_code(bron.code)
        if not code:
            raise MappingFout(f"seminar {bron.oid} zonder code")

        if bron.locatie_stad:
            locatie_stad = tekst(bron.locatie_stad.naam)
            locatie_postcode = tekst(bron.locatie_stad.postcode)
        else:
            locatie_stad, locatie_postcode = None, None

        return Doelgegevens(
            sleutels={"id": code},
            velden={
                "titel": tekst(bron.naam),
                "beschrijving": tekst(bron.onderwerp),
                "status": context.status,
                "categorie": context.categorie,
                "locatie_naam": bron.locatie_naam,
                "locatie_straat": bron.locatie_straat,
                "locatie_stad": locatie_stad,
                "locatie_postcode": locatie_postcode,
                "starttijd": bron.starttijd,
                "eindtijd": bron.eindtijd,
            }
        )


class IntegreatDeelnemerTypeMapper(Mapper[IntegreatParticipantType, None, DeelnemerType]):
    """DeelnemerType uit een Integreat-deelnemerstype.

    Integreat heeft geen brongegevens voor prijs, quota of inschrijvingsperiode.
    Die placeholders staan nu in velden_bij_aanmaak. In de oude code zaten ze
    bij de defaults met timezone.now(), waardoor elke run de ingevulde prijs en
    quota wiste en de inschrijvingsperiode naar het huidige moment opschoof.
    """

    def map(self, bron: IntegreatParticipantType, context: None = None) -> Doelgegevens[DeelnemerType]:
        return Doelgegevens(
            sleutels={"id": str(bron.oid)},
            velden={"naam": tekst(bron.naam)}
        )


class IntegreatDeelnemerMapper(Mapper[IntegreatParticipant, Any, Deelnemer]):
    """Deelnemer uit een Integreat-deelnemer plus de ledenopzoeking.

    De context is het LidGegevens-object uit de SOAP-opzoeking, of None als de
    opzoeking niets opleverde. Anders dan bij Weez wordt er hier geen deelnemer
    met foutboodschap bewaard, want bij een migratie wil je geen half
    ingevulde leden aanmaken. De inschrijving wordt dan overgeslagen.
    """

    def map(self, bron: IntegreatParticipant, context: Any) -> Doelgegevens[Deelnemer]:
        lidnummer = tekst(bron.lid_id)
        if not lidnummer:
            raise MappingFout("deelnemer zonder lidnummer")
        if context is None:
            raise MappingFout(f"geen ledengegevens gevonden voor lidnummer {lidnummer}")

        return Doelgegevens(
            sleutels={"id": lidnummer},
            velden={
                "voornaam": tekst(context.voornaam),
                "achternaam": tekst(context.naam),
                "mailadres": tekst(context.emailadres),
            },
        )


@dataclass(frozen=True)
class InschrijvingContext:
    """Alle drie zijn al bewaard voor de inschrijving gemapt wordt."""

    evenement: Evenement
    deelnemer: Deelnemer
    deelnemertype: DeelnemerType


class IntegreatInschrijvingMapper(Mapper[IntegreatRegistration, InschrijvingContext, Inschrijving]):
    """Inschrijving uit een Integreat-registratie.

    Alleen de oid is sleutel. In de oude code stonden evenement en lid er ook
    bij, waardoor een gewijzigd evenement of lid geen bestaande rij meer vond
    en er een tweede rij met dezelfde primaire sleutel aangemaakt werd.
    """

    def map(self, bron: IntegreatRegistration, context: InschrijvingContext) -> Doelgegevens[Inschrijving]:
        return Doelgegevens(
            sleutels={"id": bron.oid},
            velden={
                "evenement": context.evenement,
                "lid": context.deelnemer,
                "deelnemertype": context.deelnemertype,
                "tijdstip": bron.tijdstip,
                "prijs": bron.price,
                "annulatie": bron.annulatie,
                "annulatie_reden": bron.canceledmotivation,
            },
        )


class IntegreatVraagTypeMapper(Mapper[IntegreatSeminarFreeFieldType, None, EvenementVraagType]):
    """EvenementVraagType, ontdubbeld op naam.

    In de oude code hoorden items_vereist en items_toegestaan bij de
    opzoeksleutels, waardoor een gewijzigd aantal een tweede type met dezelfde
    naam aanmaakte. Nu zijn ze gewone velden.
    """

    def map(
        self, bron: IntegreatSeminarFreeFieldType, context: None = None
    ) -> Doelgegevens[EvenementVraagType]:
        naam = normaliseer_code(bron.code)
        if not naam:
            raise MappingFout("vraagtype zonder code")

        return Doelgegevens(
            sleutels={"naam": naam},
            velden={
                "items_vereist": bron.itemsrequired,
                "items_toegestaan": bron.itemsallowed,
            },
        )


@dataclass(frozen=True)
class VraagContext:
    """Het evenement en het vraagtype zijn al bewaard."""

    evenement: Evenement
    type: EvenementVraagType


class IntegreatEvenementVraagMapper(Mapper[IntegreatSeminarFreeField, VraagContext, EvenementVraag]):
    """EvenementVraag uit een vrij veld van een seminar."""

    def map(self, bron: IntegreatSeminarFreeField, context: VraagContext) -> Doelgegevens[EvenementVraag]:
        vraag = tekst(bron.question)
        if not vraag:
            raise MappingFout(f"vrij veld {bron.oid} zonder vraagtekst")

        return Doelgegevens(
            sleutels={"id": bron.oid},
            velden={
                "type": context.type,
                "evenement": context.evenement,
                "vraag": vraag,
                "items": bron.items,
                "vereist": bron.required,
                "volgorde": bron.sortorder,
            },
        )


@dataclass(frozen=True)
class AntwoordContext:
    """De vraag en de inschrijving bestaan pas na hun eigen synchronisatiestap."""

    vraag: EvenementVraag
    inschrijving: Inschrijving


class IntegreatAntwoordMapper(
    Mapper[IntegreatRegistrationfreefield, AntwoordContext, InschrijvingVraagAntwoord]
):
    """InschrijvingVraagAntwoord uit een antwoord op een vrij veld."""

    def map(
        self, bron: IntegreatRegistrationfreefield, context: AntwoordContext
    ) -> Doelgegevens[InschrijvingVraagAntwoord]:
        return Doelgegevens(
            sleutels={"id": bron.oid},
            velden={
                "vraag": context.vraag,
                "inschrijving": context.inschrijving,
                "antwoord": bron.answer,
            },
        )