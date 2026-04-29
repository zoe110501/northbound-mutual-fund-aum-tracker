from __future__ import annotations

import json
from pathlib import Path

from .models import ManagerSource


def load_manager_sources(path: Path) -> dict[str, ManagerSource]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources: dict[str, ManagerSource] = {}
    for item in payload["managers"]:
        source = ManagerSource(
            name=item["name"],
            official_site=item["official_site"],
            seed_urls=tuple(item.get("seed_urls") or [item["official_site"]]),
            enabled=bool(item.get("enabled", True)),
            discover_links=bool(item.get("discover_links", True)),
            max_discovered_links=int(item.get("max_discovered_links", 20)),
        )
        sources[source.name] = source
    return sources

