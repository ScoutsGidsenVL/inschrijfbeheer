"""
Mapping- en dedupliceerlogica om records uit de oude Integreat-databank
("integreat") om te zetten naar de nieuwe modellen (standaarddatabank).

Elke laad_*-functie leest uit de integreat-databank en schrijft naar de
standaarddatabank, via get_or_create/update_or_create zodat een herhaalde
run van de synchronisatie geen dubbels aanmaakt. Elke functie geeft een
QueryInfoType terug: (aangemaakt, bijgewerkt, overgeslagen).
"""

import re
from django.utils import timezone

from migratie.models import (
    Categorie,
    Inschrijving,
    DeelnemerType,
    Evenement,
    EvenementStatus,
    IntegreatParticipantType,
    IntegreatSeminar,
    IntegreatSeminarStatus,
    IntegreatSeminarType,
    Locatie,
    IntegreatRegistration,
    IntegreatSeminarFreeFieldType,
    EvenementVraagType,
    IntegreatSeminarFreeField,
    EvenementVraag,
    IntegreatRegistrationfreefield,
    InschrijvingVraagAntwoord
)

QueryInfoType = tuple[int, int, int]

_HUISNUMMER_PATROON = re.compile(r"^(?P<straat>.*\D)\s*(?P<huisnummer>\d+\w*)\s*$")


def _splits_straat_en_nummer(adres: str) -> tuple[str, str]:
    """Splits '<straatnaam> <huisnummer>' in aparte straatnaam en huisnummer

    Args:
        adres (str): string die straatnaam en huisnummer bevat

    Returns:
        tuple[str, str]: straatnaam, huisnummer
    """
    adres = (adres or "").strip()
    match = _HUISNUMMER_PATROON.match(adres)
    if not match:
        return adres, ""
    return match.group("straat").strip(), match.group("huisnummer").strip()


def haal_of_maak_locatie(seminar: IntegreatSeminar) -> Locatie:
    """Maakt een nieuwe locatie of geeft een al bestaande match

    Args:
        seminar (IntegreatSeminar): Seminar uit de Integreat databank

    Raises:
        ValueError: Gooit een error als geen adres gegeven is

    Returns:
        Locatie: Nieuwe locatie of al bestaande locatie
    """
    straat, huisnummer = _splits_straat_en_nummer(seminar.locatie_straat)
    stad = seminar.locatie_stad
    naam = seminar.locatie_naam

    if stad is None:
        if naam == '':
            raise ValueError("Geen locatie gegeven voor seminar")
        postcode = None
        stad = None
    else:
        postcode = stad.postcode
        stad = stad.naam

    locatie, _ = Locatie.objects.get_or_create(
        naam=naam,
        straat=straat,
        huisnummer=huisnummer,
        postcode=postcode,
        stad=stad,
    )
    return locatie


def haal_of_maak_status(seminar_status: IntegreatSeminarStatus) -> EvenementStatus:
    """Maakt een nieuwe EvenementStatus of geeft een bestaande terug.
    Deduplicatie gebeurt ahv `beschrijving`, er kunnen dus geen 2 statussen met dezelfde beschrijving bestaan.

    Args:
        seminar_status (IntegreatSeminarStatus): Status uit de Integreat databank

    Returns:
        EvenementStatus: nieuwe `EvenementStatus` of al bestaande
    """
    status, _ = EvenementStatus.objects.get_or_create(
        beschrijving=(seminar_status.beschrijving or "").strip(),
    )
    return status


def haal_of_maak_categorie(seminar_type: IntegreatSeminarType) -> Categorie:
    """Maakt een nieuwe Categorie aan voor een evemenent of geeft een bestaande terug.
    Maakt gebruik van de ID van het originele object als primaire sleutel.
    
    Args:
        seminar_type (IntegreatSeminarType): Type uit de Integreat databank

    Returns:
        Categorie: nieuwe `Categorie` of al bestaande
    """
    categorie, _ = Categorie.objects.update_or_create(
        id=seminar_type.code.strip(),
        defaults={
            "naam": (seminar_type.naam or "").strip(),
            # Integreat_SeminarType heeft geen apart alt_naam-veld.
            "alt_naam": (seminar_type.naam or "").strip(),
        },
    )
    return categorie


def map_evenement(seminar: IntegreatSeminar) -> dict:
    """Maakt een mapping voor een `Evenement` aan ahv een Seminar uit de Integreat databank

    Args:
        seminar (IntegreatSeminar): oude Seminar van Integreat

    Returns:
        dict: dict met de nodige attributen voor een `Evenement`
    """
    status = haal_of_maak_status(seminar.status)
    locatie = haal_of_maak_locatie(seminar)
    categorie = haal_of_maak_categorie(seminar.type)

    return {
        "titel": (seminar.naam or "").strip(),
        "beschrijving": (seminar.onderwerp or "").strip(),
        "status": status,
        "locatie": locatie,
        "starttijd": seminar.starttijd,
        "eindtijd": seminar.eindtijd,
        "categorie": categorie,
        "min_deelnemers": 0,
        "max_deelnemers": 0,
        "aantal_zelfde_groep": 0,
        "min_leeftijd": 0,
    }


def laad_evenementen(limiet: None | int = None) -> QueryInfoType:
    """Laad objecten uit de Integreat databank en zet deze om naar nieuwe objecten van het type `Evenement`.
    Maakt de nodige andere objecten aan om geen foreign key constraints te schenden.

    Args:
        limiet (None | int, optional): limiet voor het aantal in te laden objecten. Defaults to None.

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    seminars = IntegreatSeminar.objects.using("integreat").all()
    if limiet is not None:
        seminars = seminars[:limiet]

    for seminar in seminars:
        if not seminar.code:
            overgeslagen += 1
            continue

        try:
            gegevens = map_evenement(seminar)
        except Exception as fout:
            print(f"Seminar {seminar.oid} ({seminar.code}) overgeslagen: {fout}")
            overgeslagen += 1
            continue

        _, is_nieuw = Evenement.objects.update_or_create(
            id=seminar.code.strip(),
            defaults=gegevens,
        )

        if is_nieuw:
            aangemaakt += 1
        else:
            bijgewerkt += 1

    return aangemaakt, bijgewerkt, overgeslagen


def laad_deelnemertypes(limiet: None | int = None) -> QueryInfoType:
    """Laad objecten uit de Integreat databank en zet deze om naar nieuwe objecten van het type `DeelnemerType`.
    Maakt de nodige andere objecten aan om geen foreign key constraints te schenden.

    Args:
        limiet (None | int, optional): limiet voor het aantal in te laden objecten. Defaults to None.

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    types = IntegreatParticipantType.objects.using("integreat").order_by("oid")
    if limiet is not None:
        types = types[:limiet]

    for type in types:
        _, is_nieuw = DeelnemerType.objects.update_or_create(
            id=str(type.oid),
            defaults={
                "naam": (type.naam or "").strip(),
                # OPEN VRAAG: Integreat_ParticipantType heeft geen
                # brongegevens voor prijs, quota of inschrijvingsperiode
                # -> placeholders tot dit is uitgeklaard
                "prijs": 0,
                "quota": 0,
                "starttijd_inschrijvingen": timezone.now(),
                "eindtijd_inschrijvingen": timezone.now(),
            },
        )

        if is_nieuw:
            aangemaakt += 1
        else:
            bijgewerkt += 1

    return aangemaakt, bijgewerkt, overgeslagen


def laad_inschrijvingen(limiet: None | int = None) -> QueryInfoType:
    """Laad objecten uit de Integreat databank en zet deze om naar nieuwe objecten van het type `Inschrijving`.
    Maakt de nodige andere objecten aan om geen foreign key constraints te schenden.

    Args:
        limiet (None | int, optional): limiet voor het aantal in te laden objecten. Defaults to None.

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    registraties: list[IntegreatRegistration] = (
        IntegreatRegistration.objects.using("integreat")
        .select_related("seminar", "deelnemer")
        .order_by("oid")
    )
    if limiet is not None:
        registraties = registraties[:limiet]

    for registratie in registraties:
        seminar = registratie.seminar
        deelnemer = registratie.deelnemer

        if not seminar.code or not deelnemer.lid_id:
            overgeslagen += 1
            continue

        try:
            evenement = Evenement.objects.get(id=seminar.code.strip())
            deelnemertype = DeelnemerType.objects.get(id=str(registratie.deelnemers_type.oid))
        except (Evenement.DoesNotExist, DeelnemerType.DoesNotExist) as fout:
            print(f"Inschrijving {registratie.oid} overgeslagen: {fout}")
            overgeslagen += 1
            continue

        _, is_nieuw = Inschrijving.objects.update_or_create(
            id=registratie.oid,
            evenement=evenement,
            lid=deelnemer.lid_id,
            defaults={
                "deelnemertype": deelnemertype,
                "tijdstip": registratie.tijdstip,
                "prijs": registratie.price,
                "annulatie": registratie.annulatie,
                "annulatie_reden": registratie.canceledmotivation,
            },
        )

        if is_nieuw:
            aangemaakt += 1
        else:
            bijgewerkt += 1

    return aangemaakt, bijgewerkt, overgeslagen


def laad_evenement_vraagtypes(limiet: None | int = None) -> QueryInfoType:
    """Functie die EvenementVraagType objecten overzet van de oude naar de nieuwe databank

    Args:
        limiet (None | int, optional): limiet voor aantal in te laden objecten. Defaults to None.

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    types = IntegreatSeminarFreeFieldType.objects.using("integreat").all()

    if limiet is not None:
        types = types[:limiet]

    for type in types:
        _, is_nieuw = EvenementVraagType.objects.get_or_create(
            naam=type.code,
            items_vereist=type.itemsrequired,
            items_toegestaan=type.itemsallowed
        )

        if is_nieuw:
            aangemaakt += 1
        else:
            bijgewerkt += 1

    return aangemaakt, bijgewerkt, overgeslagen

def laad_evenement_vragen(limiet: None | int = None) -> QueryInfoType:
    """Functie die EvenementVraag objecten overzet van de oude databank naar de nieuwe

    Args:
        limiet (None | int, optional): limiet voor aantal in te laden objecten. Defaults to None.

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    vragen: list[IntegreatSeminarFreeField] = IntegreatSeminarFreeField.objects.using("integreat").all()

    if limiet is not None:
        vragen = vragen[:limiet]

    for vraag in vragen:
        try:
            type = EvenementVraagType.objects.get(naam=vraag.type.code)
            evenement = Evenement.objects.get(id=vraag.seminar.code)
        except (Evenement.DoesNotExist, EvenementVraagType.DoesNotExist) as e:
            overgeslagen += 1
            continue

        _, is_nieuw = EvenementVraag.objects.get_or_create(
            id=vraag.oid,
            type=type,
            vraag=vraag.question,
            items=vraag.items,
            evenement=evenement,
            vereist=vraag.required,
            volgorde=vraag.sortorder
        )

        if is_nieuw:
            aangemaakt += 1
        else:
            bijgewerkt += 1

    return aangemaakt, bijgewerkt, overgeslagen

def laad_inschrijving_vraagantwoorden(limiet: None | int = None) -> QueryInfoType:
    """Functie die InschrijvingVraagAntwoord objecten overzet van de oude databank naar de nieuwe

    Args:
        limiet (None | int, optional): limiet voor aantal in te laden objecten. Defaults to None.

    Returns:
        QueryInfoType: geeft aan hoeveel objecten werden aangemaakt, gewijzigd en overgeslagen
    """
    aangemaakt = bijgewerkt = overgeslagen = 0

    antwoorden: list[IntegreatRegistrationfreefield] = IntegreatRegistrationfreefield.objects.using("integreat").filter(answer__isnull=False).exclude(answer="")

    if limiet is not None:
        antwoorden = antwoorden[:limiet]

    for antwoord in antwoorden:
        try:
            vraag = EvenementVraag.objects.get(id=antwoord.field.oid)
            inschrijving = Inschrijving.objects.get(id=antwoord.registration.oid)
        except (EvenementVraag.DoesNotExist, Inschrijving.DoesNotExist) as e:
            overgeslagen += 1
            continue

        _, is_nieuw = InschrijvingVraagAntwoord.objects.get_or_create(
            id=antwoord.oid,
            vraag=vraag,
            antwoord=antwoord.answer,
            inschrijving=inschrijving,
        )

        if is_nieuw:
            aangemaakt += 1
        else:
            bijgewerkt += 1

    return aangemaakt, bijgewerkt, overgeslagen