"""Module met met hulpfuncties voor de API van Weez

## Functies:
    **doe_weez_patch:** maakt een PATCH request naar de Weez API met de nodige extra parameters
"""

import json
import os

from dotenv import load_dotenv
from requests import Response, Session

load_dotenv()
BASE_URL = os.getenv("WEEZ_BASE_URL")
WEEZ_ACCESS_TOKEN = os.getenv("WEEZ_ACCESS_TOKEN")
WEEZ_API_KEY = os.getenv("WEEZ_API_KEY")


def maak_sessie() -> Session:
    return Session()


def doe_weez_patch(sessie: Session, url: str, data: dict) -> Response:
    """Doet een PATCH request naar de API van Weez met de nodige data

    Args:
        sessie (Session): sessie waarbinnen de requests gemaakt kunnen worden
        url (str): url waar de request gemaakt moet worden, exclusief BASE_URL
        data (dict): dict die als JSON wordt meegestuurd in het "data"-veld van de request

    Returns:
        Response: respons van de API

    Raises:
        HTTPError: indien de request een foutstatus ontvangt
    """
    response = sessie.patch(
        f"{BASE_URL}{url}",
        data={
            "api_key": WEEZ_API_KEY,
            "access_token": WEEZ_ACCESS_TOKEN,
            "data": json.dumps(data),
        },
        timeout=10,
    )
    response.raise_for_status()

    return response.json()
