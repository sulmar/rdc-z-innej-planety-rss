"""Modele danych przechowywane w data/episodes.json."""

from __future__ import annotations

from dataclasses import dataclass, field, fields


def _from_dict(cls, data: dict):
    known = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Podcast:
    id: str
    slug: str
    title: str
    description: str = ""
    image: str | None = None
    link: str = ""
    pages_count: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Podcast:
        return _from_dict(cls, data)


@dataclass
class Episode:
    id: str
    title: str
    date: str  # ISO 8601 (YYYY-MM-DD); RDC nie podaje godziny
    duration_s: int | None = None
    description_html: str = ""
    image: str | None = None
    author: str | None = None
    mp3_url: str | None = None
    mp3_length: int | None = None
    # Pozycja wśród odcinków z tego samego dnia (0 = najnowszy) – służy do wyliczenia godziny w pubDate.
    day_rank: int = 0
    first_seen: str | None = None
    checked_at: str | None = None

    @property
    def is_complete(self) -> bool:
        return bool(self.mp3_url and self.mp3_length)

    @classmethod
    def from_dict(cls, data: dict) -> Episode:
        return _from_dict(cls, data)


@dataclass
class State:
    podcast: Podcast | None = None
    episodes: dict[str, Episode] = field(default_factory=dict)
