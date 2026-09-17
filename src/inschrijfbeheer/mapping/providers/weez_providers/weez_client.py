"""Client voor de Weezevent API.

Regelt het ophalen en vernieuwen van het access token (OAuth2 client credentials)
zodat je zelf alleen nog endpoints hoeft aan te roepen.

Env-variabelen:
    WEEZ_ACCESS_CLIENT_ID       verplicht
    WEEZ_ACCESS_CLIENT_SECRET   verplicht
    WEEZ_API_BASE_URL           optioneel, standaard https://api.weezevent.com

Gebruik:
    from weez_client import WeezClient

    with WeezClient() as weez:
        events = weez.get("/events")
        for deelnemer in weez.paginate("/participant/list", params={"id_event": 123}):
            print(deelnemer)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Iterator, Mapping, Sequence

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
logger = logging.getLogger(__name__)

TOKEN_URL = os.getenv("ACCOUNTS_URL")


class WeezError(Exception):
    """Basisfout voor alles wat misloopt in deze client."""


class WeezAuthError(WeezError):
    """Het ophalen van een access token lukte niet."""


class WeezAPIError(WeezError):
    """De API antwoordde met een foutstatus."""

    def __init__(self, status_code: int, url: str, body: Any) -> None:
        self.status_code = status_code
        self.url = url
        self.body = body
        super().__init__(f"{status_code} op {url}: {body!r}")


class WeezClient:
    """Eén client voor al je Weezevent-requests.

    Het access token komt automatisch binnen bij het eerste request en vernieuwt
    zichzelf zodra het bijna vervalt. Je hoeft er verder niets mee te doen.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        token_url: str = TOKEN_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        expiry_margin: int = 60,
        organisatie: str = "",
    ) -> None:
        self.client_id = client_id or os.environ.get("WEEZ_ACCESS_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("WEEZ_ACCESS_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise WeezAuthError(
                "Zet WEEZ_ACCESS_CLIENT_ID en WEEZ_ACCESS_CLIENT_SECRET in je omgeving "
                "of geef ze mee aan WeezClient(...)."
            )

        self.organisatie = organisatie or os.getenv("WEEZ_ORGANISATIE_ID")
        self.token_url = token_url
        self.timeout = timeout
        self.expiry_margin = expiry_margin

        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._lock = threading.Lock()

        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"Accept": "application/json"})

    @property
    def access_token(self) -> str:
        """Een geldig access token. Haalt of vernieuwt het waar nodig."""
        with self._lock:
            if not self._token or time.time() >= self._token_expires_at:
                self._fetch_token()
            return self._token  # type: ignore[return-value]

    def _fetch_token(self) -> None:
        logger.debug("Nieuw access token ophalen bij %s", self.token_url)
        try:
            response = self.session.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise WeezAuthError(f"Token ophalen mislukte: {exc}") from exc

        if response.status_code != 200:
            raise WeezAuthError(
                f"Token ophalen mislukte met status {response.status_code}. "
                f"Controleer je client id en secret. Antwoord: {response.text}"
            )

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise WeezAuthError(f"Geen access_token in het antwoord: {payload!r}")

        self._token = token
        self._token_expires_at = (
            time.time() + int(payload.get("expires_in", 300)) - self.expiry_margin
        )
        logger.debug("Token geldig tot %s", self._token_expires_at)

    def invalidate_token(self) -> None:
        """Gooi het huidige token weg zodat het volgende request een nieuw ophaalt."""
        with self._lock:
            self._token = None
            self._token_expires_at = 0.0

    def _url(self, path: str) -> str:
        if not path.startswith(("http://", "https://")):
            raise ValueError("Pad moet beginnen met http(s)://")
        return path

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        headers: Mapping[str, str] | None = None,
        raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Voer een request uit tegen de API en geef de JSON terug.

        Zet raw=True als je het volledige requests.Response-object wil,
        bijvoorbeeld voor een download of een endpoint zonder JSON.
        """
        url = self._url(path)
        request_headers = {"Authorization": f"Bearer {self.access_token}"}
        if headers:
            request_headers.update(headers)

        timeout = kwargs.pop("timeout", self.timeout)

        def send() -> requests.Response:
            try:
                return self.session.request(
                    method.upper(),
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=request_headers,
                    timeout=timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                raise WeezError(f"Request naar {url} mislukte: {exc}") from exc

        response = send()

        # Token afgekeurd? Eén keer vernieuwen en opnieuw proberen.
        if response.status_code == 401:
            logger.debug("401 ontvangen, token vernieuwen en opnieuw proberen")
            self.invalidate_token()
            request_headers["Authorization"] = f"Bearer {self.access_token}"
            response = send()

        if response.status_code >= 400:
            raise WeezAPIError(response.status_code, url, _safe_body(response))

        if raw:
            return response
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        page_param: str = "page",
        size_param: str = "max",
        page_size: int = 100,
        start_page: int = 1,
        items_key: str | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Loop door alle pagina's en geef de items één voor één terug.

        De Weezevent-endpoints gebruiken page en max. Wijkt een endpoint af,
        pas dan page_param en size_param aan.
        """
        query = dict(params or {})
        query[size_param] = page_size
        page = start_page
        pages_done = 0

        while True:
            query[page_param] = page
            payload = self.get(path, params=query, **kwargs)
            items = _extract_items(payload, items_key)
            if not items:
                return
            yield from items

            pages_done += 1
            if max_pages is not None and pages_done >= max_pages:
                return
            if len(items) < page_size:
                return
            page += 1

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "WeezClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<WeezClient base_url={self.base_url!r}>"


def _extract_items(payload: Any, items_key: str | None) -> Sequence[Any]:
    """Haal de lijst met items uit een antwoord, ook als die in een sleutel zit."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if items_key:
            return payload.get(items_key) or []
        for key in ("data", "items", "results", "participants", "events"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        lists = [v for v in payload.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
    return []


def _safe_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
