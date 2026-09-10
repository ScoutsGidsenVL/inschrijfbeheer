from dataclasses import dataclass

from inschrijfbeheer.models import (

    Evenement,
    EvenementVraag,
)

from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, Mapper, MappingFout

def _normaliseer(waarde) -> str:
    return "" if waarde is None else str(waarde).strip()


STANDAARD_ALIASSEN = frozenset({
    "adresse", "adressedelivraison", "adresse_societe", "billet_prix", "blog",
    "choix_place", "civilite", "codepostaldelivraison", "code_postal",
    "code_postal_societe", "commentaires", "date_de_naissance", "email",
    "email_pro", "fonction", "member_code", "nom", "pays", "paysdelivraison",
    "pays_societe", "portable", "portable_societe", "prenom", "site_internet",
    "societe", "telephone", "validity_date_start", "ville", "villedelivraison",
    "ville_societe",
})


def alias_van_label(label: str) -> str | None:
    """Geeft de standaardalias van een vraag, of None bij een eigen vraag.

    Weez labelt haar standaardvragen met de alias zelf, alleen met een
    hoofdletter ("Date_de_naissance" voor "date_de_naissance").
    """
    alias = (label or "").strip().lower().replace(" ", "_")
    return alias if alias in STANDAARD_ALIASSEN else None


def weez_sleutel_van(vraag: EvenementVraag) -> str:
    """Geeft de sleutel waarmee Weez deze vraag aanspreekt in het form-veld."""
    return alias_van_label(vraag.vraag) or vraag.id

def koppel_eigen_vragen(antwoorden: list[dict], form: dict) -> dict[int, str]:
    """Bepaalt het Weez-vraag-id van elke eigen vraag.

    De standaardvragen vallen aan beide kanten weg, de rest blijft in de
    volgorde van het formulier staan. Klopt het aantal niet, dan valt de
    koppeling terug op de waarde, en enkel als die eenduidig is.

    Args:
        antwoorden (list[dict]): "answers" uit de oude API, met label en value
        form (dict): "form" uit de v3-API, sleutel naar waarde

    Returns:
        dict[int, str]: positie in de antwoordenlijst naar Weez-vraag-id
    """
    posities = [
        positie for positie, antwoord in enumerate(antwoorden)
        if alias_van_label(antwoord.get("label")) is None
    ]
    ids = [sleutel for sleutel in form if sleutel not in STANDAARD_ALIASSEN]

    if len(posities) == len(ids):
        return dict(zip(posities, ids))

    logger.warning(
        "Weez gaf %s eigen vragen en %s eigen antwoorden, koppeling valt terug op de waarde",
        len(ids), len(posities),
    )

    gekoppeld = {}
    beschikbaar = {vraag_id: _normaliseer(form[vraag_id]) for vraag_id in ids}
    for positie in posities:
        gezocht = _normaliseer(antwoorden[positie].get("value"))
        kandidaten = [
            vraag_id for vraag_id, waarde in beschikbaar.items()
            if waarde == gezocht and waarde != ""
        ]
        if len(kandidaten) == 1:
            vraag_id = kandidaten.pop()
            gekoppeld[positie] = vraag_id
            del beschikbaar[vraag_id]

    return gekoppeld


@dataclass(frozen=True)
class VraagContext:
    """De volgorde komt uit de positie in de antwoordenlijst, niet uit de brondata."""

    evenement: Evenement
    volgorde: int
    weez_vraag_id: str | None = None


class WeezEvenementVraagMapper(Mapper[dict, VraagContext, EvenementVraag]):
    """Vraag van een evenement, uit een antwoord van een deelnemer.

    Weez levert de vragen niet apart, enkel per deelnemer samen met het
    antwoord. Dezelfde vraag komt dus bij elke deelnemer opnieuw voorbij. Een
    eigen vraag wordt ontdubbeld op het Weez-vraag-id, een standaardvraag op
    haar label, want die heeft bij Weez geen eigen id.
    """

    def map(self, bron: dict, context: VraagContext) -> Doelgegevens[EvenementVraag]:
        label = bron.get("label")
        if not label:
            raise MappingFout("vraag zonder label")

        if alias_van_label(label):
            return Doelgegevens(
                sleutels={"evenement": context.evenement, "vraag": label},
                velden={"volgorde": context.volgorde},
            )

        if not context.weez_vraag_id:
            raise MappingFout(f"geen Weez-vraag-id gevonden voor eigen vraag {label}")

        return Doelgegevens(
            sleutels={"id": context.weez_vraag_id},
            velden={
                "evenement": context.evenement,
                "vraag": label,
                "volgorde": context.volgorde,
            },
        )