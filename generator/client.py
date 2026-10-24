"""Klient HTTP – jedyne miejsce z ruchem sieciowym.

Pilnuje pauzy między zapytaniami (N2), ponawia błędy przejściowe i rozpoznaje blokadę Cloudflare.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable

import httpx

log = logging.getLogger(__name__)


class SourceBlockedError(RuntimeError):
    """Źródło zwróciło stronę weryfikacji Cloudflare zamiast treści."""


def is_cloudflare_challenge(status_code: int, text: str) -> bool:
    return status_code in (403, 503) and (
        "challenges.cloudflare.com" in text or "<title>Just a moment" in text
    )


class HttpClient:
    def __init__(
        self,
        user_agent: str,
        delay_s: float,
        timeout_s: float = 30.0,
        retries: int = 3,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Language": "pl,en;q=0.5"},
            timeout=timeout_s,
            follow_redirects=True,
            transport=transport,
        )
        self._delay_s = delay_s
        self._retries = retries
        self._sleep = sleep
        self._last_request = 0.0
        self.request_count = 0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        for attempt in range(1, self._retries + 1):
            wait = self._last_request + self._delay_s - time.monotonic()
            if wait > 0:
                self._sleep(wait)
            self._last_request = time.monotonic()
            self.request_count += 1
            log.debug("%s %s", method, url)
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                error: Exception = exc
            else:
                if method == "GET" and is_cloudflare_challenge(response.status_code, response.text):
                    raise SourceBlockedError(f"Cloudflare zablokował dostęp do {url}")
                if response.status_code < 500:
                    return response
                error = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}", request=response.request, response=response
                )
            if attempt == self._retries:
                raise error
            backoff = 2**attempt
            log.warning("%s %s: %s – ponowienie za %d s", method, url, error, backoff)
            self._sleep(backoff)
        raise AssertionError("unreachable")

    def get_text(self, url: str) -> str:
        response = self._request("GET", url)
        response.raise_for_status()
        return response.text

    def content_length(self, url: str) -> int | None:
        """Rozmiar pliku w bajtach (HEAD, a gdy brak nagłówka – GET z Range na 1 bajt)."""
        response = self._request("HEAD", url)
        if response.status_code == 200 and response.headers.get("content-length"):
            return int(response.headers["content-length"])
        response = self._request("GET", url, headers={"Range": "bytes=0-0"})
        match = re.search(r"/(\d+)$", response.headers.get("content-range", ""))
        return int(match.group(1)) if response.status_code == 206 and match else None
