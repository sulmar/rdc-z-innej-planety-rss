"""Aktualizacja stanu: wykrycie nowych odcinków na liście i uzupełnienie ich danych (docs/architecture.md §5)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

import httpx

from . import parser
from .config import Config
from .models import Episode, Podcast, State

log = logging.getLogger(__name__)


class Client(Protocol):
    def get_text(self, url: str) -> str: ...
    def content_length(self, url: str) -> int | None: ...


@dataclass
class SyncResult:
    pages_fetched: int = 0
    new: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def sync(
    client: Client,
    config: Config,
    state: State,
    *,
    from_page: int = 1,
    to_page: int | None = None,
    stop_when_no_new: bool = True,
    on_page_done: Callable[[int], None] | None = None,
    now: Callable[[], datetime] = _now,
) -> SyncResult:
    """Przegląda strony listy od `from_page`.

    Tryb przyrostowy (`stop_when_no_new=True`): kończy na pierwszej stronie bez nowych odcinków
    lub po `config.max_pages_incremental` stronach. Import archiwum: przechodzi do `to_page`
    (domyślnie ostatnia strona) i zapisuje stan po każdej stronie przez `on_page_done`.
    """
    if to_page is None and stop_when_no_new:
        to_page = from_page + config.max_pages_incremental - 1

    result = SyncResult()
    seen_order: list[str] = []
    page = from_page
    while True:
        html = client.get_text(config.list_url(page))
        result.pages_fetched += 1

        if page == 1 or state.podcast is None:
            _update_podcast(state, config, html)

        listing = parser.parse_episode_list(html, config.podcast_id, config.media_base_url)
        if not listing.items:
            raise parser.ParseError(f"Strona {page} listy nie zawiera żadnych odcinków")
        if state.podcast is not None and listing.pages_count:
            state.podcast.pages_count = listing.pages_count

        new_on_page = 0
        for item in listing.items:
            seen_order.append(item.id)
            episode = state.episodes.get(item.id)
            if episode is None:
                episode = Episode(id=item.id, title=item.title, date=item.date.isoformat(),
                                  first_seen=now().isoformat())
                state.episodes[item.id] = episode
                result.new.append(item.id)
                new_on_page += 1
            episode.title = item.title
            episode.date = item.date.isoformat()
            episode.duration_s = item.duration_s
            episode.description_html = item.description_html
            if not episode.is_complete:
                _fetch_details(client, config, episode, result, now)

        _assign_day_ranks(state, seen_order)
        log.info("Strona %d: %d odcinków, nowych: %d", page, len(listing.items), new_on_page)
        if on_page_done is not None:
            on_page_done(page)

        last_page = listing.pages_count or page
        if stop_when_no_new and new_on_page == 0:
            break
        if page >= last_page or (to_page is not None and page >= to_page):
            break
        page += 1

    # Odcinki, którym wcześniej nie udało się pobrać MP3, a nie było ich na przejrzanych stronach.
    seen = set(seen_order)
    for episode in state.episodes.values():
        if not episode.is_complete and episode.id not in seen:
            _fetch_details(client, config, episode, result, now)

    return result


def _update_podcast(state: State, config: Config, html: str) -> None:
    info = parser.parse_podcast(html, config.media_base_url)
    podcast = state.podcast or Podcast(id=config.podcast_id, slug=config.podcast_slug, title=info.title)
    podcast.title = info.title
    podcast.description = info.description
    podcast.image = info.image or podcast.image
    podcast.link = config.public_podcast_url()
    state.podcast = podcast


def _fetch_details(client: Client, config: Config, episode: Episode, result: SyncResult,
                   now: Callable[[], datetime]) -> None:
    try:
        html = client.get_text(config.episode_url(episode.id))
        details = parser.parse_episode_page(html, config.media_base_url)
    except (httpx.HTTPStatusError, parser.ParseError) as exc:
        log.warning("Odcinek %s (%s): %s", episode.id, episode.title, exc)
        result.failed.append(episode.id)
        return
    if not details.mp3_url:
        log.warning("Odcinek %s (%s): brak pliku MP3 na stronie", episode.id, episode.title)
        result.failed.append(episode.id)
        return
    length = client.content_length(details.mp3_url)
    if not length:
        log.warning("Odcinek %s: nie udało się ustalić rozmiaru %s", episode.id, details.mp3_url)
        result.failed.append(episode.id)
        return
    episode.mp3_url = details.mp3_url
    episode.mp3_length = length
    episode.author = details.author or episode.author
    episode.image = details.image or episode.image
    episode.checked_at = now().isoformat()
    result.completed.append(episode.id)
    log.info("Nowy odcinek %s: %s (%s)", episode.id, episode.title, episode.date)


def _assign_day_ranks(state: State, order: list[str]) -> None:
    """Numeruje odcinki z tego samego dnia w kolejności z listy RDC (0 = najnowszy)."""
    counters: dict[str, int] = {}
    for episode_id in dict.fromkeys(order):  # bez duplikatów, gdy lista przesunęła się między stronami
        episode = state.episodes[episode_id]
        episode.day_rank = counters.get(episode.date, 0)
        counters[episode.date] = episode.day_rank + 1
