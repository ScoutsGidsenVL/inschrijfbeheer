"""Scans doorsturen naar Weezevent.

Deze module zet één scan op de juiste checkpoint-url van Weezevent:

    POST /access/organizations/{organization_id}/checkpoints/{checkpoint_id}/scans
    {"uuid": "...", "device_name": "...", "status": 1, "barcode": 12341234}

Instellingen (settings.py of .env, settings wint):
    WEEZ_ORGANISATIE_ID   organisatie van je Weezevent-account
    WEEZ_CHECKPOINT_ID    checkpoint waarop je registreert
    WEEZ_DEVICE_NAME      naam die in Weezevent bij de scan verschijnt,
                          standaard "Django"

Gebruik:
    from .weezevent_scans import stuur_scan, WeezScanFout

    stuur_scan("12341234", status=1)
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any
from uuid import uuid4

from django.conf import settings

from inschrijfbeheer.mapping.providers.weez_providers.weez_client import WeezClient, WeezError

logger = logging.getLogger(__name__)

_client: WeezClient | None = None
_client_lock = threading.Lock()


class WeezScanFout(Exception):
    """De scan raakte niet tot bij Weezevent."""


def get_client() -> WeezClient:
    """Eén gedeelde client per proces, zodat het token hergebruikt wordt."""
    global _client
    with _client_lock:
        if _client is None:
            _client = WeezClient()
        return _client


def _instelling(naam: str, standaard: str | None = None) -> str | None:
    waarde = os.getenv(naam)
    return waarde or standaard


def _als_barcode(barcode: Any) -> Any:
    """Weezevent verwacht een getal als de barcode er een is."""
    tekst = str(barcode).strip()
    return int(tekst) if tekst.isdigit() else tekst


def stuur_scan(
    barcode: Any,
    *,
    status: int = 1,
    device_name: str | None = None,
    checkpoint_id: str | None = None,
    organisatie_id: str | None = None,
    client: WeezClient | None = None,
) -> Any:
    """Registreer één scan op een checkpoint.

    status 1 zet de deelnemer binnen, status 0 draait de registratie terug.
    Loopt er iets mis, dan krijg je een WeezScanFout.
    """
    if barcode in (None, ""):
        raise WeezScanFout("Zonder barcode vertrekt er geen scan naar Weezevent.")

    client = client or get_client()
    organisatie_id = organisatie_id or client.organisatie
    checkpoint_id = checkpoint_id or _instelling("WEEZ_CHECKPOINT_ID", "1")
    device_name = device_name or _instelling("WEEZ_DEVICE_NAME", "Django")

    if not organisatie_id:
        raise WeezScanFout("Zet WEEZ_ORGANISATIE_ID in je settings of je omgeving.")

    payload = {
        "uuid": str(uuid4()),
        "status": int(status),
        "barcode": _als_barcode(barcode),
    }
    pad = f"/access/organizations/{organisatie_id}/checkpoints/1/scans"

    logger.debug("Scan versturen naar %s: %s", pad, payload)
    try:
        return client.post(pad, json=payload)
    except WeezError as fout:
        raise WeezScanFout(f"Weezevent weigerde de scan: {fout}") from fout