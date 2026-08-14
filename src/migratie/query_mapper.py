"""
Dit bestand bevat alle functies die gebruikt kunnen worden om de datavelden in de modellen in de juiste volgorde te zetten voor de query voor het aanmaken in de databank.
"""

from modellen import *

def maak_evenement_query_arg(evenement: Evenement) -> tuple[str, str, str, int, int, datetime, datetime, int, int, int, int, str]:
    return (
        evenement.id,
        evenement.titel,
        evenement.beschrijving,
        evenement.status,
        evenement.locatie,
        evenement.starttijd,
        evenement.eindtijd,
        evenement.min_deelnemers,
        evenement.max_deelnemers,
        evenement.aantal_zelfde_groep,
        evenement.min_leeftijd,
        evenement.categorie
    )

def maak_inschrijving_query_arg(inschrijving: Inschrijving) -> tuple[str, str, str, datetime, bool, bool, bool]:
    pass

def maak_categorie_query_arg(categorie: Categorie) -> tuple:
    return (
        categorie.id,
        categorie.naam,
        categorie.alt_naam
    )

def maak_locatie_query_arg(locatie: Locatie) -> tuple:
    return (
        locatie.id,
        locatie.naam,
        locatie.straat,
        locatie.huisnummer,
        locatie.postcode,
        locatie.stad
    )