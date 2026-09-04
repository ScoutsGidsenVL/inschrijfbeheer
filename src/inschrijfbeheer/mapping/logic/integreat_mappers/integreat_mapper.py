"""Mappers van de Integreat-databank naar de nieuwe Inschrijfbeheer-modellen.

De brondata is hier geen JSON maar een modelinstantie uit de databank
"integreat", dus T is telkens een Integreat-model. Verder geldt hetzelfde als
bij de Weez-mappers: geen databankwerk, geen tellers, geen netwerkaanroepen,
en wat niet omzetbaar is wordt een MappingFout.

De get_or_create- en update_or_create-aanroepen uit de oude laad_*-functies
zitten nu in de sleutels en velden van Doelgegevens. Synchronisatie.bewaar()
voert ze uit en telt wat er gebeurde.
"""

def tekst(waarde: str | None) -> str:
    """Maakt witruimte en None onschadelijk.
    """
    return (waarde or "").strip()


def normaliseer_code(code: str | None) -> str:
    """De code van een seminar of seminartype is de sleutel in de nieuwe databank.
    """
    return tekst(code)