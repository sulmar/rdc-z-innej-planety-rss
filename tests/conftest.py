from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from generator.config import Config

FIXTURES = Path(__file__).parent / "fixtures"
PODCAST_ID = "fY7TF0S0caRGGuoABNJe"
MEDIA = "https://www.rdc.pl"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeClient:
    """Odpowiada zapisanymi stronami RDC; każdy odcinek dostaje stronę szczegółów z próbki."""

    def __init__(self, config: Config, pages: dict[int, str], mp3_length: int | None = 1000):
        self.config = config
        self.pages = pages
        self.mp3_length = mp3_length
        self.requests: list[str] = []

    def get_text(self, url: str) -> str:
        self.requests.append(url)
        for page, html in self.pages.items():
            if url == self.config.list_url(page):
                return html
        if "?episode=" in url:
            return fixture("episode_LVHL34Ee9ix5OGapcwGo.html")
        raise AssertionError(f"Nieoczekiwany URL: {url}")

    def content_length(self, url: str) -> int | None:
        self.requests.append(f"HEAD {url}")
        return self.mp3_length

    @property
    def episode_requests(self) -> list[str]:
        return [u for u in self.requests if "?episode=" in u]


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        request_delay_s=0,
        feed_url="https://example.github.io/rdc/feed.xml",
        data_path=tmp_path / "episodes.json",
        output_path=tmp_path / "feed.xml",
    )


@pytest.fixture
def fixed_now():
    return lambda: datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
