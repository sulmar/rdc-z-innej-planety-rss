"""Walidacja kanału przed publikacją (docs/architecture.md §6)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

from .feed import NS


def count_items(xml_text: str) -> int:
    try:
        return len(ET.fromstring(xml_text).findall("./channel/item"))
    except ET.ParseError:
        return 0


def validate_feed(xml_text: str, previous_count: int | None = None) -> list[str]:
    """Zwraca listę błędów; pusta lista oznacza kanał gotowy do publikacji."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return [f"Niepoprawny XML: {exc}"]

    errors: list[str] = []
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        return ["Brak elementu <rss><channel>"]
    if not (channel.findtext("title") or "").strip():
        errors.append("Kanał nie ma tytułu")

    items = channel.findall("item")
    if not items:
        errors.append("Kanał nie zawiera żadnego odcinka")
    if previous_count is not None and len(items) < previous_count:
        errors.append(f"Mniej odcinków niż w poprzedniej wersji ({len(items)} < {previous_count})")

    guids: set[str] = set()
    for index, item in enumerate(items, 1):
        guid = (item.findtext("guid") or "").strip()
        label = f"Odcinek {index} ({guid or 'bez guid'})"
        if not guid:
            errors.append(f"{label}: brak guid")
        elif guid in guids:
            errors.append(f"{label}: zduplikowany guid")
        guids.add(guid)
        if not (item.findtext("title") or "").strip():
            errors.append(f"{label}: brak tytułu")
        try:
            parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            errors.append(f"{label}: brak lub niepoprawny pubDate")
        enclosure = item.find("enclosure")
        if enclosure is None:
            errors.append(f"{label}: brak enclosure")
            continue
        if not enclosure.get("url", "").startswith("https://"):
            errors.append(f"{label}: enclosure url musi być adresem https")
        if not enclosure.get("length", "").isdigit() or int(enclosure.get("length")) <= 0:
            errors.append(f"{label}: niepoprawny enclosure length")
        if enclosure.get("type") != "audio/mpeg":
            errors.append(f"{label}: enclosure type inny niż audio/mpeg")
        duration = item.findtext(f"{{{NS['itunes']}}}duration")
        if duration is not None and not duration.replace(":", "").isdigit():
            errors.append(f"{label}: niepoprawny itunes:duration")

    return errors


def validate_file(path: Path, previous_count: int | None = None) -> list[str]:
    if not path.exists():
        return [f"Plik {path} nie istnieje"]
    return validate_feed(path.read_text(encoding="utf-8"), previous_count)
