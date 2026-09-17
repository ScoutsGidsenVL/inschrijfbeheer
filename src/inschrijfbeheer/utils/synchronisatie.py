"""Eén evenement synchroniseren met zijn bron.

Bedoeld voor de interface en voor de achtergrondtaak:

    from inschrijfbeheer.mapping.sync_evenement import synchroniseer_evenement

    info = synchroniseer_evenement(evenement)
    messages.success(request, info.formatteer())

Welke bron gebruikt wordt, volgt uit evenement.is_weez. Het evenement.id is in
beide gevallen de identifier die de bron nodig heeft: bij Weez het Weez-id, bij
Integreat de seminarcode.

Dit bestand doet zelf niets meer dan de juiste syncer kiezen. Het ophalen,
omzetten en bewaren gebeurt in WeezSyncer en IntegreatSyncer, zodat één
evenement en een volledige synchronisatie niet uit elkaar groeien.
"""

from functools import partial

from inschrijfbeheer.mapping import SynchronisatieConfig, SynchronisatieInfo
from inschrijfbeheer.mapping.integreat_syncer import IntegreatSyncer
from inschrijfbeheer.mapping.synchronisatie import Synchronisatie
from inschrijfbeheer.mapping.weez_syncer import WeezSyncer
from inschrijfbeheer.models import Evenement


def maak_syncer(evenement: Evenement) -> Synchronisatie:
    """Kiest de syncer die bij dit evenement hoort.

    sync_alles staat aan, want je vraagt dit evenement uitdrukkelijk op. Het
    terugblikvenster van de geplande synchronisatie telt hier dus niet.
    """
    klasse = WeezSyncer if evenement.is_weez else IntegreatSyncer
    return klasse(SynchronisatieConfig(sync_alles=True))


def synchroniseer_evenement(evenement: Evenement) -> SynchronisatieInfo:
    """Haalt één evenement opnieuw op bij zijn bron, met inschrijvingen, vragen en antwoorden.

    Alles gebeurt in één transactie, dus een fout halverwege laat geen half
    bijgewerkt evenement achter.

    Args:
        evenement (Evenement): het evenement dat opnieuw opgehaald wordt

    Returns:
        SynchronisatieInfo: wat er aangemaakt, bijgewerkt en overgeslagen is.
            Bestaat het evenement niet meer bij de bron, dan staat het als
            overgeslagen geregistreerd en volgt er geen fout.

    Raises:
        requests.RequestException: als de Weez-API onbereikbaar is
        django.db.Error: bij een databankfout, bijvoorbeeld wanneer de
            Integreat-databank niet bereikbaar is
    """
    syncer = maak_syncer(evenement)

    return syncer.voer_uit(
        partial(syncer.synchroniseer_evenement, str(evenement.id), sync_inschrijvingen=True)
    )
