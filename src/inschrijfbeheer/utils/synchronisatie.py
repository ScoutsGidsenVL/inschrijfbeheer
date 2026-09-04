"""Eén evenement synchroniseren met zijn bron, rechtstreeks via de providers en mappers.

Bedoeld voor de interface:

    from inschrijfbeheer.mapping.sync_evenement import synchroniseer_evenement

    info = synchroniseer_evenement(evenement)
    messages.success(request, info.formatteer)

Dit bestand gebruikt de syncers niet. Het leest rechtstreeks bij de providers,
zet om met de mappers en bewaart zelf, zodat je in één bestand kan volgen wat
er gebeurt. De volledige synchronisatie blijft via WeezSyncer en
IntegreatSyncer lopen.

Welke bron gebruikt wordt, volgt uit evenement.is_weez. Het evenement.id is in
beide gevallen de identifier die de bron nodig heeft: bij Weez het Weez-id, bij
Integreat de seminarcode.
"""

import logging

from django.db import transaction

from inschrijfbeheer.mapping.providers.data_provider import IntegreatFilter
from inschrijfbeheer.mapping.providers.integreat_providers import (
    IntegreatRegistrationfreefieldProvider,
    IntegreatRegistrationProvider,
    IntegreatSeminarFreeFieldProvider,
    IntegreatSeminarProvider,
)
from inschrijfbeheer.mapping.providers.lid_provider import LidProvider
from inschrijfbeheer.mapping.logic.mapper import Doelgegevens, MappingFout
from inschrijfbeheer.mapping.logic.integreat_mappers.integreat_mapper import (
    AntwoordContext as IntegreatAntwoordContext,
)
from inschrijfbeheer.mapping.logic.integreat_mappers.integreat_mapper import (
    EvenementContext as IntegreatEvenementContext,
)
from inschrijfbeheer.mapping.logic.integreat_mappers.integreat_mapper import (
    InschrijvingContext as IntegreatInschrijvingContext,
)
from inschrijfbeheer.mapping.logic.integreat_mappers.integreat_mapper import (
    IntegreatAntwoordMapper,
    IntegreatCategorieMapper,
    IntegreatDeelnemerMapper,
    IntegreatDeelnemerTypeMapper,
    IntegreatEvenementMapper,
    IntegreatEvenementVraagMapper,
    IntegreatInschrijvingMapper,
    IntegreatStatusMapper,
    IntegreatVraagTypeMapper,
    normaliseer_code,
)
from inschrijfbeheer.mapping.logic.integreat_mappers.integreat_mapper import VraagContext as IntegreatVraagContext
from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import AntwoordContext as WeezAntwoordContext
from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import (
    InschrijvingContext as WeezInschrijvingContext,
)
from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import VraagContext as WeezVraagContext
from inschrijfbeheer.mapping.logic.weez_mappers.weez_mappers import (
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
from inschrijfbeheer.mapping.providers.weez_providers import (
    InschrijvingFilter,
    WeezClient,
    WeezEvenementProvider,
    WeezInschrijvingProvider,
    WeezTariefProvider,
)
from inschrijfbeheer.mapping.synchronisatie import SynchronisatieActie, SynchronisatieInfo
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

AANGEMAAKT = SynchronisatieActie.AANGEMAAKT
BIJGEWERKT = SynchronisatieActie.BIJGEWERKT
OVERGESLAGEN = SynchronisatieActie.OVERGESLAGEN


def bewaar(model, doel: Doelgegevens, info: SynchronisatieInfo, enkel_aanmaken: bool = False):
    """Bewaart Doelgegevens en houdt bij wat er gebeurde."""
    if enkel_aanmaken:
        bewaard, aangemaakt = model.objects.get_or_create(
            **doel.sleutels, defaults={**doel.velden}
        )
        if aangemaakt:
            info.registreer(model, AANGEMAAKT)
        return bewaard

    else:
        bewaard, aangemaakt = model.objects.update_or_create(
            **doel.sleutels, defaults=doel.velden
        )

    info.registreer(model, AANGEMAAKT if aangemaakt else BIJGEWERKT)
    return bewaard


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
    info = SynchronisatieInfo()
    bron = "WEEZ" if evenement.is_weez else "INTEGREAT"
    logger.info("[%s SYNC] Evenement %s (%s)", bron, evenement.id, evenement.titel)

    with transaction.atomic():
        if evenement.is_weez:
            __synchroniseer_weez(evenement, info)
        else:
            __synchroniseer_integreat(evenement, info)

    logger.info("[%s SYNC] %s", bron, info.formatteer())
    return info


def __synchroniseer_weez(evenement: Evenement, info: SynchronisatieInfo) -> None:
    with WeezClient() as client:
        evenement_provider = WeezEvenementProvider(client)
        inschrijving_provider = WeezInschrijvingProvider(client)
        tarief_provider = WeezTariefProvider(client)
        lid_provider = LidProvider()

        bron = evenement_provider.haal_op(str(evenement.id))
        if not bron:
            logger.warning("Evenement %s bestaat niet meer bij Weez", evenement.id)
            info.registreer(Evenement, OVERGESLAGEN)
            return

        try:
            categorie = None
            categorie_bron = bron.get("category") or {}
            if categorie_bron:
                categorie = bewaar(
                    Categorie,
                    WeezCategorieMapper().map(categorie_bron, None),
                    info,
                    enkel_aanmaken=True,
                )
            doel_evenement = bewaar(
                Evenement, WeezEvenementMapper().map(bron, categorie), info
            )
        except MappingFout as fout:
            logger.warning("Evenement %s overgeslagen: %s", evenement.id, fout)
            info.registreer(Evenement, OVERGESLAGEN)
            return

        tarieven = tarief_provider.haal_tarieven_op(str(evenement.id))
        deelnemers = inschrijving_provider.haal_alle_op(
            InschrijvingFilter(evenement_id=str(evenement.id))
        )

        for deelnemer_bron in deelnemers:
            vragen = deelnemer_bron.get("answers") or []

            # Ontbreekt er een verplichte vraag, dan geldt dat voor het hele
            # formulier en dus voor alle deelnemers van dit evenement.
            if not check_verplichte_vragen(vragen):
                logger.warning(
                    "Evenement %s (%s) mist een verplichte vraag",
                    doel_evenement.titel,
                    doel_evenement.id,
                )
                doel_evenement.foutboodschap = (
                    "Evenement mist een verplichte vraag, inschrijvingen worden "
                    "niet gesynchroniseerd"
                )
                doel_evenement.save()
                return

            gegevens = bepaal_inschrijvingsgegevens(vragen)
            if gegevens is None:
                logger.warning("Deelnemer met onvolledige ledengegevens overgeslagen")
                info.registreer(Inschrijving, OVERGESLAGEN)
                continue

            try:
                resultaat = los_lid_op(lid_provider, gegevens)
                deelnemer = bewaar(
                    Deelnemer, WeezDeelnemerMapper().map(gegevens, resultaat), info
                )
                inschrijving = bewaar(
                    Inschrijving,
                    WeezInschrijvingMapper().map(
                        deelnemer_bron,
                        WeezInschrijvingContext(
                            evenement=doel_evenement, deelnemer=deelnemer, tarieven=tarieven
                        ),
                    ),
                    info,
                )
            except MappingFout as fout:
                logger.warning("Inschrijving overgeslagen: %s", fout)
                info.registreer(Inschrijving, OVERGESLAGEN)
                continue

            for volgorde, vraag_bron in enumerate(vragen):
                try:
                    vraag = bewaar(
                        EvenementVraag,
                        WeezEvenementVraagMapper().map(
                            vraag_bron,
                            WeezVraagContext(evenement=doel_evenement, volgorde=volgorde),
                        ),
                        info,
                    )
                    bewaar(
                        InschrijvingVraagAntwoord,
                        WeezAntwoordMapper().map(
                            vraag_bron,
                            WeezAntwoordContext(vraag=vraag, inschrijving=inschrijving),
                        ),
                        info,
                    )
                except MappingFout as fout:
                    logger.warning("Vraag of antwoord overgeslagen: %s", fout)
                    info.registreer(InschrijvingVraagAntwoord, OVERGESLAGEN)


def __synchroniseer_integreat(evenement: Evenement, info: SynchronisatieInfo) -> None:
    code = normaliseer_code(str(evenement.id))
    bron_filter = IntegreatFilter(sync_alles=True)
    lid_provider = LidProvider()

    seminar = IntegreatSeminarProvider().haal_op(code)
    if seminar is None:
        logger.warning("Seminar met code %s bestaat niet meer in Integreat", code)
        info.registreer(Evenement, OVERGESLAGEN)
        return

    try:
        status = bewaar(
            EvenementStatus,
            IntegreatStatusMapper().map(seminar.status, None),
            info,
            enkel_aanmaken=True,
        )
        categorie = bewaar(Categorie, IntegreatCategorieMapper().map(seminar.type, None), info)
        doel_evenement = bewaar(
            Evenement,
            IntegreatEvenementMapper().map(
                seminar, IntegreatEvenementContext(status=status, categorie=categorie)
            ),
            info,
        )
    except MappingFout as fout:
        logger.warning("Seminar %s overgeslagen: %s", code, fout)
        info.registreer(Evenement, OVERGESLAGEN)
        return

    # De inschrijvingen van dit seminar. Het contains-filter doet het grove
    # werk in de databank, de exacte vergelijking gebeurt daarna in Python
    # omdat Code met opvulruimte in de bron staat.
    inschrijvingen_per_oid = {}
    registraties = IntegreatRegistrationProvider().haal_alle_op(bron_filter)
    for registratie in registraties.filter(seminar__code__contains=code):
        if registratie.deelnemer is None or registratie.deelnemers_type is None:
            logger.warning("Registratie %s zonder deelnemer of type", registratie.oid)
            info.registreer(Inschrijving, OVERGESLAGEN)
            continue

        try:
            # Het deelnemerstype hangt al aan de registratie, dus daar is geen
            # aparte ophaalstap voor nodig.
            deelnemertype = bewaar(
                DeelnemerType,
                IntegreatDeelnemerTypeMapper().map(registratie.deelnemers_type, None),
                info,
            )
            lidnummer = (registratie.deelnemer.lid_id or "").strip()
            deelnemer = bewaar(
                Deelnemer,
                IntegreatDeelnemerMapper().map(
                    registratie.deelnemer, lid_provider.haal_op(lidnummer)
                ),
                info,
            )
            inschrijvingen_per_oid[registratie.oid] = bewaar(
                Inschrijving,
                IntegreatInschrijvingMapper().map(
                    registratie,
                    IntegreatInschrijvingContext(
                        evenement=doel_evenement,
                        deelnemer=deelnemer,
                        deelnemertype=deelnemertype,
                    ),
                ),
                info,
            )
        except MappingFout as fout:
            logger.warning("Registratie %s overgeslagen: %s", registratie.oid, fout)
            info.registreer(Inschrijving, OVERGESLAGEN)

    # De vragen van dit seminar.
    vragen_per_oid = {}
    vrije_velden = IntegreatSeminarFreeFieldProvider().haal_alle_op(bron_filter)
    for vrij_veld in vrije_velden.filter(seminar__code__contains=code):
        if normaliseer_code(getattr(vrij_veld.seminar, "code", None)) != code:
            continue

        try:
            vraagtype = bewaar(
                EvenementVraagType, IntegreatVraagTypeMapper().map(vrij_veld.type, None), info
            )
            vragen_per_oid[vrij_veld.oid] = bewaar(
                EvenementVraag,
                IntegreatEvenementVraagMapper().map(
                    vrij_veld,
                    IntegreatVraagContext(evenement=doel_evenement, type=vraagtype),
                ),
                info,
            )
        except MappingFout as fout:
            logger.warning("Vrij veld %s overgeslagen: %s", vrij_veld.oid, fout)
            info.registreer(EvenementVraag, OVERGESLAGEN)

    # De antwoorden erop. Vraag en inschrijving komen uit de twee dicts
    # hierboven, dus daar is geen extra opzoeking voor nodig.
    antwoorden = IntegreatRegistrationfreefieldProvider().haal_alle_op(bron_filter)
    for antwoord in antwoorden.filter(registration__seminar__code__contains=code):
        vraag = vragen_per_oid.get(antwoord.field_id)
        inschrijving = inschrijvingen_per_oid.get(antwoord.registration_id)
        if vraag is None or inschrijving is None:
            continue

        try:
            bewaar(
                InschrijvingVraagAntwoord,
                IntegreatAntwoordMapper().map(
                    antwoord,
                    IntegreatAntwoordContext(vraag=vraag, inschrijving=inschrijving),
                ),
                info,
            )
        except MappingFout as fout:
            logger.warning("Antwoord %s overgeslagen: %s", antwoord.oid, fout)
            info.registreer(InschrijvingVraagAntwoord, OVERGESLAGEN)