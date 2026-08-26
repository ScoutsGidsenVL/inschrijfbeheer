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

from .models import (
    Categorie,
    Inschrijving,
    DeelnemerType,
    Evenement,
    EvenementStatus,
    IntegreatParticipantType,
    IntegreatParticipant,
    IntegreatSeminar,
    IntegreatSeminarStatus,
    IntegreatSeminarType,
    Locatie,
    IntegreatRegistration
)

QueryInfoType = tuple[int, int, int]

_HUISNUMMER_PATROON = re.compile(r"^(?P<straat>.*\D)\s*(?P<huisnummer>\d+\w*)\s*$")


def _splits_straat_en_nummer(adres: str) -> tuple[str, str]:
    adres = (adres or "").strip()
    match = _HUISNUMMER_PATROON.match(adres)
    if not match:
        return adres, ""
    return match.group("straat").strip(), match.group("huisnummer").strip()


def haal_of_maak_locatie(seminar: IntegreatSeminar) -> Locatie:
    """
    Zoekt of maakt een Locatie op basis van de adresvelden van het seminar.

    Omdat er geen extern ID is om op te matchen, wordt hier gededuplice-
    erd op de combinatie straat + huisnummer + postcode + stad.
    """
    straat, huisnummer = _splits_straat_en_nummer(seminar.locatie_straat)
    stad = seminar.locatie_stad
    naam = seminar.locatie_naam

    if stad is None:
        if naam == '':
            raise Exception("Geen locatie gegeven")
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


def haal_of_maak_status(oude_status: IntegreatSeminarStatus) -> EvenementStatus:
    """
    EvenementStatus heeft evenmin een extern-ID-veld, dus dedupliceren
    gebeurt op de beschrijving zelf. Twee statussen met exact dezelfde
    beschrijving worden dus altijd als dezelfde status behandeld.
    """
    status, _ = EvenementStatus.objects.get_or_create(
        beschrijving=(oude_status.beschrijving or "").strip(),
    )
    return status


def haal_of_maak_categorie(oud_type: IntegreatSeminarType) -> Categorie:
    """
    Categorie.id is een CharField, dus we gebruiken de businesscode van
    het seminartype (Code) als primaire key. Die is stabiel over meerdere
    runs, in tegenstelling tot een automatisch ID.
    """
    categorie, _ = Categorie.objects.update_or_create(
        id=oud_type.code.strip(),
        defaults={
            "naam": (oud_type.naam or "").strip(),
            # Integreat_SeminarType heeft geen apart alt_naam-veld.
            "alt_naam": (oud_type.naam or "").strip(),
        },
    )
    return categorie


def map_evenement(seminar: IntegreatSeminar) -> dict:
    """
    Zet een IntegreatSeminar om naar de velden van het nieuwe Evenement.

    OPEN VRAAG: Integreat_Seminar heeft geen bronveld voor
    min_deelnemers, max_deelnemers, aantal_zelfde_groep of min_leeftijd
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
        aangemaakt += int(is_nieuw)
        bijgewerkt += int(not is_nieuw)

    return aangemaakt, bijgewerkt, overgeslagen


def laad_deelnemertypes(limiet: None | int = None) -> QueryInfoType:
    """
    Laad alle bestaande deelnemertypes in van Integreat.
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
        aangemaakt += int(is_nieuw)
        bijgewerkt += int(not is_nieuw)

    return aangemaakt, bijgewerkt, overgeslagen


def laad_inschrijvingen(limiet: None | int = None) -> QueryInfoType:
    """
    Laad inschrijvingen in van Integreat.
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
            evenement=evenement,
            lid=deelnemer.lid_id,
            defaults={
                "deelnemertype": deelnemertype,
                "tijdstip": registratie.tijdstip,
                # OPEN VRAAG: Integreat_Registration heeft geen apart veld
                # voor betaal- of terugbetalingsstatus -> placeholders
                "is_betaald": False,
                "is_geannuleerd": registratie.annulatie is not None,
                "is_terugbetaald": False,
            },
        )
        aangemaakt += int(is_nieuw)
        bijgewerkt += int(not is_nieuw)

    return aangemaakt, bijgewerkt, overgeslagen