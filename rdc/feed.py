"""Budowa kanału RSS 2.0 z rozszerzeniami Apple Podcasts – zawsze w całości ze stanu (decyzja D5)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, time, timedelta
from email.utils import format_datetime
from zoneinfo import ZoneInfo

from .config import Config
from .models import Episode, State
from .parser import normalize_newlines

WARSAW = ZoneInfo("Europe/Warsaw")
# RDC podaje tylko datę publikacji – przyjmujemy południe, a kolejne odcinki dnia cofamy o sekundy.
PUBLISH_TIME = time(12, 0)

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "atom": "http://www.w3.org/2005/Atom",
}
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)


def _q(name: str) -> str:
    prefix, _, local = name.partition(":")
    return f"{{{NS[prefix]}}}{local}" if local else name


def _sub(parent: ET.Element, name: str, text: str | None = None, attrs: dict[str, str] | None = None) -> ET.Element:
    element = ET.SubElement(parent, _q(name), {_q(k): v for k, v in (attrs or {}).items()})
    if text is not None:
        element.text = text
    return element


def pub_date(episode: Episode) -> datetime:
    day = date.fromisoformat(episode.date)
    return datetime.combine(day, PUBLISH_TIME, WARSAW) - timedelta(seconds=episode.day_rank)


def format_duration(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def feed_episodes(state: State, config: Config) -> list[Episode]:
    episodes = [ep for ep in state.episodes.values() if ep.is_complete]
    episodes.sort(key=lambda ep: (pub_date(ep), ep.id), reverse=True)
    if config.feed_max_items is not None:
        episodes = episodes[: config.feed_max_items]
    return episodes


def build_feed(state: State, config: Config) -> str:
    podcast = state.podcast
    if podcast is None:
        raise ValueError("Brak danych audycji – najpierw uruchom `sync`")
    episodes = feed_episodes(state, config)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = _sub(rss, "channel")
    _sub(channel, "title", podcast.title)
    _sub(channel, "link", podcast.link or config.public_podcast_url())
    _sub(channel, "description", podcast.description or podcast.title)
    _sub(channel, "language", "pl")
    if config.feed_url:
        _sub(channel, "atom:link", attrs={"href": config.feed_url, "rel": "self", "type": "application/rss+xml"})
    if episodes:
        # Z danych, nie z zegara – ponowna generacja bez zmian daje identyczny plik.
        _sub(channel, "lastBuildDate", format_datetime(pub_date(episodes[0])))
    _sub(channel, "generator", "rdc-podcast-feed")
    _sub(channel, "itunes:author", "Polskie Radio RDC")
    _sub(channel, "itunes:summary", podcast.description or podcast.title)
    if podcast.image:
        _sub(channel, "itunes:image", attrs={"href": podcast.image})
        image = _sub(channel, "image")
        _sub(image, "url", podcast.image)
        _sub(image, "title", podcast.title)
        _sub(image, "link", podcast.link or config.public_podcast_url())
    _sub(channel, "itunes:category", attrs={"text": "Science"})
    _sub(channel, "itunes:explicit", "false")
    _sub(channel, "itunes:type", "episodic")
    # Kanał prywatny – nie trafia do katalogu Apple Podcasts.
    _sub(channel, "itunes:block", "Yes")

    for episode in episodes:
        item = _sub(channel, "item")
        _sub(item, "title", episode.title)
        _sub(item, "link", config.public_episode_url(episode.id))
        _sub(item, "guid", episode.id, {"isPermaLink": "false"})
        _sub(item, "pubDate", format_datetime(pub_date(episode)))
        description = normalize_newlines(episode.description_html or episode.title)
        _sub(item, "description", description)
        _sub(item, "content:encoded", description)
        _sub(item, "enclosure", attrs={"url": episode.mp3_url, "length": str(episode.mp3_length), "type": "audio/mpeg"})
        if episode.duration_s:
            _sub(item, "itunes:duration", format_duration(episode.duration_s))
        if episode.author:
            _sub(item, "itunes:author", episode.author)
        if episode.image:
            _sub(item, "itunes:image", attrs={"href": episode.image})
        _sub(item, "itunes:episodeType", "full")
        _sub(item, "itunes:explicit", "false")

    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"
