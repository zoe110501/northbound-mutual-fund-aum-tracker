from __future__ import annotations

import re

from .models import FundRecord


JPMORGAN_FACTSHEET_BASE = "https://am.jpmorgan.com/content/dam/jpm-am-aem/asiapacific/hk/en/literature/fact-sheet"
JPMORGAN_FACTSHEET_SLUGS = {
    "jpmorgan asian total return bond fund": "jpmorgan_asian_total_return_bond_e.pdf",
    "jpmorgan pacific securities fund": "jpmorgan_pacific_securities_e.pdf",
    "jpmorgan asia equity dividend fund": "jpmorgan_asia_equity_dividend_e.pdf",
    "jpmorgan global bond fund": "jpmorgan_global_bond_e.pdf",
    "jpmorgan pacific technology fund": "jpmorgan_pacific_tech_e.pdf",
    "jpmorgan asia growth fund": "jpmorgan_asia_growth_e.pdf",
    "jpmorgan sar hong kong fund": "jpmorgan_sar_hong_kong_e.pdf",
}


def adapter_urls_for_manager(manager: str, targets: list[FundRecord]) -> list[str]:
    urls: list[str] = []
    manager_key = manager.strip()
    if manager_key in {"摩根基金(亚洲)", "摩根资管(亚太)"}:
        urls.extend(_jpmorgan_urls(targets))
    return list(dict.fromkeys(urls))


def _jpmorgan_urls(targets: list[FundRecord]) -> list[str]:
    urls: list[str] = []
    for target in targets:
        key = normalize_name(target.english_name)
        slug = JPMORGAN_FACTSHEET_SLUGS.get(key)
        if slug:
            urls.append(f"{JPMORGAN_FACTSHEET_BASE}/{slug}")
    return urls


def normalize_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip().lower()
    return value
