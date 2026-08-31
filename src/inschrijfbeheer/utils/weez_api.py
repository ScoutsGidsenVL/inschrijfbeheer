"""Module met met hulpfuncties voor de API van Weez

## Functies:
    **doe_weez_get:** maakt een GET request naar de Weez API met de nodige extra parameters
"""
from requests import get, Response, Session
import os
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("WEEZ_BASE_URL")
WEEZ_ACCESS_TOKEN = os.getenv("WEEZ_ACCESS_TOKEN")
WEEZ_API_KEY = os.getenv("WEEZ_API_KEY")

def maak_sessie() -> Session:
    return Session()

def doe_weez_get(sessie: Session, url: str) -> Response:
    """Doet een GET request naar de API van Weez met de nodige extra parameters

    Args:
        url (str): url waar de request gemaakt moet worden, exclusief BASE_URL

    Returns:
        Response: respons van de API
    """
    return get(f"{BASE_URL}{url}?api_key={WEEZ_API_KEY}&access_token={WEEZ_ACCESS_TOKEN}", timeout=10)