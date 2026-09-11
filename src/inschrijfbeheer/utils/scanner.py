"""Toegangscontrole via de WeezAccess-API.

WeezAccess staat los van de ticketing-API: eigen authenticatie met OAuth 2.0
client credentials, JSON in plaats van form-encoded, en een Bearer-token in
plaats van een api_key. Vandaar een eigen client.
"""

import logging
import os
import uuid as uuid_module
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from requests import Response, Session

from inschrijfbeheer.mapping.providers import WeezClient
from inschrijfbeheer.models import Inschrijving

logger = logging.getLogger("inschrijfbeheer")

ACCOUNTS_URL = "https://accounts.weezevent.com/realms/accounts/protocol/openid-connect/token"
ACCESS_BASE_URL = "https://api.weezevent.com"
WEEZ_ORGANISATIE_ID = "2397965" # gehaald uit request in weezaccess
WEEZ_ACCESS_CLIENT_ID = ""
WEEZ_ACCESS_CLIENT_SECRET = ""

SCAN_IN = 1
SCAN_UIT = 2


@dataclass(frozen=True)
class ScanResultaat:
    """Uitkomst van een scanpoging.

    Attributes:
        gelukt (bool): of WeezAccess de scan aanvaardde
        nieuw (bool): of het om een nieuwe scan ging, False als dezelfde scan
            al geregistreerd stond
        uuid (str): de scan-uuid, om mee te geven bij een herhaalpoging
        foutboodschap (str): waarom de scan geweigerd werd
        gegevens (dict | None): de scan zoals WeezAccess hem teruggeeft
    """

    gelukt: bool
    nieuw: bool = False
    uuid: str = ""
    foutboodschap: str = ""
    gegevens: dict | None = None


class WeezAccessClient:
    """Praat met de WeezAccess-API en houdt het OAuth-token bij.

    Het token vervalt na een paar minuten, dus het wordt bewaard tot vlak voor
    de vervaldatum en daarna opnieuw opgehaald.
    """

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = WEEZ_ACCESS_CLIENT_ID
        self.client_secret = WEEZ_ACCESS_CLIENT_SECRET
        self.sessie = Session()
        self.__token: str | None = None
        self.__vervalt_op = datetime.min

    def __haal_token_op(self) -> str:
        if self.__token and datetime.now() < self.__vervalt_op:
            return self.__token

        respons = self.sessie.post(
            ACCOUNTS_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10,
        )
        respons.raise_for_status()

        gegevens = respons.json()
        self.__token = gegevens["access_token"]
        # Marge van 30 seconden, zodat een token niet vervalt tijdens een request.
        self.__vervalt_op = datetime.now() + timedelta(
            seconds=int(gegevens.get("expires_in", 300)) - 30
        )
        return self.__token

    def post(self, url: str, data: dict) -> Response:
        """Doet een POST naar WeezAccess, zonder de status te controleren.

        Args:
            url (str): pad exclusief ACCESS_BASE_URL
            data (dict): body die als JSON verstuurd wordt

        Returns:
            Response: respons van de API, ook bij een foutstatus
        """
        return self.sessie.post(
            f"{ACCESS_BASE_URL}{url}",
            json=data,
            headers={"Authorization": f"Bearer {self.__haal_token_op()}"},
            timeout=10,
        )


def haal_barcode_op(client: WeezClient, inschrijving: Inschrijving) -> str | None:
    """Haalt de barcode van een inschrijving op bij de ticketing-API.

    Inschrijving bewaart de barcode niet, en WeezAccess scant net op die
    waarde. De id van de inschrijving is de id_participant bij Weez.
    """
    respons = client.get(
        f"v3/evenement/{inschrijving.evenement.id}/participants/{inschrijving.id}"
    )
    return respons.get("barcode")


def scan_inschrijving(
    inschrijving: Inschrijving,
    barcode: str | None = None,
    checkpoint_id: int | None = None,
    status: int = SCAN_IN,
    apparaat: str = "inschrijfbeheer",
    scan_uuid: str | None = None,
    access_client: WeezAccessClient | None = None,
    weez_client: WeezClient | None = None,
) -> ScanResultaat:
    """Registreert een scan voor een inschrijving op een controlepunt.

    WeezAccess past de regels van het controlepunt toe, dus een deelnemer die
    er niet door mag levert een geweigerde scan op met de reden erbij. Dat is
    geen uitzondering maar een normale uitkomst, vandaar een ScanResultaat.

    Args:
        inschrijving (Inschrijving): inschrijving die gescand wordt
        barcode (str | None, optional): barcode van het ticket. Wordt opgehaald
            bij de ticketing-API als je hem niet meegeeft.
        checkpoint_id (int | None, optional): controlepunt. Defaults to
            WEEZ_CHECKPOINT_ID uit de omgeving.
        status (int, optional): SCAN_IN of SCAN_UIT. Defaults to SCAN_IN.
        apparaat (str, optional): naam waaronder de scan bij Weez verschijnt.
        scan_uuid (str | None, optional): geef de uuid van een vorige poging
            mee om die veilig te herhalen.
        access_client (WeezAccessClient | None, optional): client voor WeezAccess.
        weez_client (WeezClient | None, optional): client voor de ticketing-API.

    Returns:
        ScanResultaat: of de scan doorging, en zo niet waarom
    """
    organisatie_id = WEEZ_ORGANISATIE_ID
    checkpoint_id = checkpoint_id or os.getenv("WEEZ_CHECKPOINT_ID")

    if barcode is None:
        if weez_client is not None:
            barcode = haal_barcode_op(weez_client, inschrijving)
        else:
            with WeezClient() as client:
                barcode = haal_barcode_op(client, inschrijving)

    if not barcode:
        return ScanResultaat(
            gelukt=False,
            foutboodschap=f"Geen barcode gevonden voor inschrijving {inschrijving.id}",
        )

    scan_uuid = scan_uuid or str(uuid_module.uuid4())
    payload = {
        "uuid": scan_uuid,
        "barcode": barcode,
        "status": status,
        "device_name": apparaat,
    }

    try:
        respons = (access_client or WeezAccessClient()).post(
            f"/access/organizations/{organisatie_id}/checkpoints/{checkpoint_id}/scans",
            payload,
        )
    except requests.RequestException as fout:
        logger.warning("Scan voor inschrijving %s mislukt: %s", inschrijving.id, fout)
        return ScanResultaat(
            gelukt=False,
            uuid=scan_uuid,
            foutboodschap="WeezAccess is niet bereikbaar, probeer straks opnieuw",
        )

    if respons.status_code in (200, 201):
        return ScanResultaat(
            gelukt=True,
            nieuw=respons.status_code == 201,
            uuid=scan_uuid,
            gegevens=respons.json(),
        )

    foutboodschap = _lees_foutboodschap(respons)
    logger.warning("Scan geweigerd voor inschrijving %s: %s", inschrijving.id, foutboodschap)
    return ScanResultaat(gelukt=False, uuid=scan_uuid, foutboodschap=foutboodschap)


def _lees_foutboodschap(respons: Response) -> str:
    """Haalt de reden uit een geweigerde scan, in welke vorm ze ook komt."""
    try:
        inhoud = respons.json()
    except ValueError:
        return respons.text.strip() or f"WeezAccess gaf status {respons.status_code}"

    if isinstance(inhoud, dict):
        for sleutel in ("message", "detail", "error"):
            if inhoud.get(sleutel):
                return str(inhoud[sleutel])
        return "; ".join(f"{sleutel}: {waarde}" for sleutel, waarde in inhoud.items())
    if isinstance(inhoud, list):
        return "; ".join(str(item) for item in inhoud)
    return str(inhoud)