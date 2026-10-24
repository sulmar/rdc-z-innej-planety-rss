"""Konfiguracja generatora: wartości domyślne nadpisywane zmiennymi środowiskowymi."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    base_url: str = "https://web.rdc.pl"
    media_base_url: str = "https://www.rdc.pl"
    podcast_path: str = "z-innej-planety_fY7TF0S0caRGGuoABNJe"
    request_delay_s: float = 1.5
    max_pages_incremental: int = 3
    feed_max_items: int | None = None
    feed_url: str | None = None
    data_path: Path = Path("data/episodes.json")
    output_path: Path = Path("public/feed.xml")
    user_agent: str = "Mozilla/5.0 (compatible; rdc-podcast-feed/0.1)"

    @property
    def podcast_slug(self) -> str:
        return self.podcast_path.rsplit("_", 1)[0]

    @property
    def podcast_id(self) -> str:
        return self.podcast_path.rsplit("_", 1)[1]

    def list_url(self, page: int) -> str:
        return f"{self.base_url}/podcast/{self.podcast_path}?active_page={page}"

    def episode_url(self, episode_id: str) -> str:
        return f"{self.base_url}/podcast/{self.podcast_path}?episode={episode_id}"

    def public_podcast_url(self) -> str:
        return f"{self.media_base_url}/podcast/{self.podcast_path}"

    def public_episode_url(self, episode_id: str) -> str:
        return f"{self.public_podcast_url()}?episode={episode_id}"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        default = cls()

        def get(name: str, fallback):
            value = env.get(name)
            return fallback if value in (None, "") else value

        max_items = get("FEED_MAX_ITEMS", None)
        return cls(
            base_url=get("RDC_BASE_URL", default.base_url).rstrip("/"),
            media_base_url=get("RDC_MEDIA_BASE_URL", default.media_base_url).rstrip("/"),
            podcast_path=get("PODCAST_PATH", default.podcast_path),
            request_delay_s=float(get("REQUEST_DELAY_S", default.request_delay_s)),
            max_pages_incremental=int(get("MAX_PAGES_INCREMENTAL", default.max_pages_incremental)),
            feed_max_items=int(max_items) if max_items is not None else None,
            feed_url=get("FEED_URL", None),
            data_path=Path(get("DATA_PATH", default.data_path)),
            output_path=Path(get("OUTPUT_PATH", default.output_path)),
            user_agent=get("USER_AGENT", default.user_agent),
        )
