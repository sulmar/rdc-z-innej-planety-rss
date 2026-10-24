"""Odczyt i atomowy zapis stanu (data/episodes.json)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .models import Episode, Podcast, State


def load(path: Path) -> State:
    if not path.exists():
        return State()
    data = json.loads(path.read_text(encoding="utf-8"))
    podcast = Podcast.from_dict(data["podcast"]) if data.get("podcast") else None
    episodes = {eid: Episode.from_dict(ep) for eid, ep in data.get("episodes", {}).items()}
    return State(podcast=podcast, episodes=episodes)


def save(state: State, path: Path) -> None:
    data = {
        "podcast": asdict(state.podcast) if state.podcast else None,
        "episodes": {eid: asdict(ep) for eid, ep in state.episodes.items()},
    }
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_atomic(path, text)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
