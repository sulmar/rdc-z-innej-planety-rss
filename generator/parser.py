"""Parsowanie HTML stron audycji RDC. Czyste funkcje, bez dostępu do sieci.

Selektory opisane są w docs/analysis.md §3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag


class ParseError(RuntimeError):
    """Strona nie ma oczekiwanej struktury (np. zmiana szablonu RDC)."""


@dataclass
class ListItem:
    id: str
    title: str
    date: date
    duration_s: int | None
    description_html: str


@dataclass
class EpisodeList:
    items: list[ListItem]
    pages_count: int | None


@dataclass
class EpisodeDetails:
    mp3_url: str | None
    title: str | None
    author: str | None
    image: str | None


@dataclass
class PodcastInfo:
    title: str
    description: str
    image: str | None


_EPISODE_ID_RE = re.compile(r"^[A-Za-z0-9]{20}$")
_BG_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")
_PAGESPEED_RE = re.compile(r"/x([^/]+?)\.pagespeed\.[a-z]{2}\.[^/.]+\.[a-z0-9]+$", re.I)
_SIZE_PREFIX_RE = re.compile(r"/(?:contain-\d+-\d+-max-|anchor_photo_front_\d+x\d+_)([^/]+)$")
_DURATION_PART_RE = re.compile(r"(\d+)\s*(godz|h|min|s)\b", re.I)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _text(node: Tag | None) -> str:
    if node is None:
        return ""
    return " ".join(node.get_text(" ", strip=True).replace("\xa0", " ").split())


def _meta(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    content = tag.get("content") if tag else None
    return content.strip() if content else None


def absolute_url(url: str, base_url: str) -> str:
    """Zamienia ścieżkę względną lub adres z innego hosta RDC na adres w `base_url`."""
    parsed = urlparse(url)
    if parsed.netloc.endswith("rdc.pl"):
        url = parsed._replace(scheme="", netloc="").geturl()
    return urljoin(base_url + "/", url)


def strip_pagespeed(url: str) -> str:
    """`/xNAZWA.pagespeed.ic.HASH.jpg` → `/NAZWA` (oryginalny plik bez przepisania mod_pagespeed)."""
    return _PAGESPEED_RE.sub(r"/\1", url)


def original_image_url(url: str) -> str:
    """Adres oryginalnego obrazu: bez mod_pagespeed i bez prefiksu wariantu rozmiaru."""
    return _SIZE_PREFIX_RE.sub(r"/\1", strip_pagespeed(url))


def parse_date(value: str) -> date:
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", value)
    if not match:
        raise ParseError(f"Nieznany format daty: {value!r}")
    day, month, year = (int(g) for g in match.groups())
    return date(year, month, day)


def parse_duration(value: str) -> int | None:
    """„48 min 08 s” → 2888. Zwraca None, gdy nie rozpoznano żadnej części."""
    total = 0
    found = False
    for number, unit in _DURATION_PART_RE.findall(value):
        found = True
        unit = unit.lower()
        total += int(number) * (3600 if unit in ("h", "godz") else 60 if unit == "min" else 1)
    return total if found else None


def _episode_id_from_href(href: str, podcast_id: str) -> str | None:
    parsed = urlparse(href)
    if not parsed.path.rstrip("/").endswith(f"_{podcast_id}"):
        return None
    ids = parse_qs(parsed.query).get("episode")
    if ids and _EPISODE_ID_RE.match(ids[0]):
        return ids[0]
    return None


def _current_episode_id(soup: BeautifulSoup, podcast_id: str) -> str | None:
    """ID odcinka w odtwarzaczu – element listy „Teraz odtwarzane” nie ma własnego linku.

    Odczytywane z przycisku „skopiuj link”, który zawsze wskazuje odtwarzany odcinek.
    """
    copy = soup.select_one("a.copyclipboard[onclick]")
    if copy is not None:
        match = re.search(r"writeText\('([^']+)'", copy["onclick"])
        if match:
            return _episode_id_from_href(match.group(1), podcast_id)
    og_url = _meta(soup, "og:url")
    return _episode_id_from_href(og_url, podcast_id) if og_url else None


def _rewrite_html_urls(fragment: Tag, base_url: str) -> str:
    for tag in fragment.find_all(src=True):
        tag["src"] = absolute_url(strip_pagespeed(tag["src"]), base_url)
    for tag in fragment.find_all(href=True):
        tag["href"] = absolute_url(tag["href"], base_url)
    return fragment.decode_contents().strip()


def parse_episode_list(html: str, podcast_id: str, media_base_url: str) -> EpisodeList:
    soup = _soup(html)
    container = soup.select_one(".myajaxlist_content")
    if container is None:
        raise ParseError("Brak listy odcinków (.myajaxlist_content)")

    pages_count = container.get("data-pagescount")
    current_id = _current_episode_id(soup, podcast_id)

    items: list[ListItem] = []
    for box in container.select(".podcast_player_box"):
        episode_id = None
        for link in box.select("a[href*='episode=']"):
            episode_id = _episode_id_from_href(link["href"], podcast_id)
            if episode_id:
                break
        if episode_id is None and "active" in box.get("class", []):
            episode_id = current_id
        if episode_id is None:
            raise ParseError("Nie udało się ustalić ID odcinka na liście")

        title = _text(box.select_one(".desc h3"))
        date_node = box.select_one(".podcast_time li.date")
        if not title or date_node is None:
            raise ParseError(f"Odcinek {episode_id}: brak tytułu lub daty")
        lead = box.select_one(".desc .lead")
        items.append(
            ListItem(
                id=episode_id,
                title=title,
                date=parse_date(_text(date_node)),
                duration_s=parse_duration(_text(box.select_one(".podcast_time li.read_time"))),
                description_html=_rewrite_html_urls(lead, media_base_url) if lead else "",
            )
        )

    return EpisodeList(items=items, pages_count=int(pages_count) if pages_count else None)


def parse_episode_page(html: str, media_base_url: str) -> EpisodeDetails:
    soup = _soup(html)
    source = soup.select_one("video.media_player source[src], audio source[src]")
    image = _meta(soup, "og:image")
    title = _text(soup.select_one(".main_title_value")) or _meta(soup, "og:title")
    return EpisodeDetails(
        mp3_url=absolute_url(source["src"], media_base_url) if source else None,
        title=title.replace("\xa0", " ") if title else None,
        author=_text(soup.select_one(".author_value .name")) or None,
        image=absolute_url(image, media_base_url) if image else None,
    )


def parse_podcast(html: str, media_base_url: str) -> PodcastInfo:
    soup = _soup(html)
    title = _text(soup.select_one(".podcast_title h1"))
    if not title:
        raise ParseError("Brak tytułu audycji (.podcast_title h1)")

    short = soup.select_one(".podcast_short_desc")
    description = ""
    image = None
    if short is not None:
        paragraphs = [_text(p) for p in short.select(".desc > p")]
        description = "\n\n".join(p for p in paragraphs if p)
        image_node = short.select_one(".image[style]")
        match = _BG_URL_RE.search(image_node["style"]) if image_node else None
        if match:
            image = absolute_url(original_image_url(match.group(1)), media_base_url)

    return PodcastInfo(title=title, description=description, image=image)
