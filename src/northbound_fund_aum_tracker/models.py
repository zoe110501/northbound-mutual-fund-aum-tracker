from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FundRecord:
    fund_code: str
    name: str
    english_name: str
    management_company: str
    source_kind: str


@dataclass(frozen=True)
class ManagerSource:
    name: str
    official_site: str
    seed_urls: tuple[str, ...]
    enabled: bool = True
    discover_links: bool = True
    max_discovered_links: int = 20


@dataclass(frozen=True)
class MoneyEvidence:
    target_name: str
    amount: float
    currency: str
    amount_usd: float
    fx_rate_to_usd: float
    source_url: str
    label: str
    context: str


@dataclass
class ManagerResult:
    manager: str
    official_site: str
    global_total_usd: float = 0.0
    mainland_total_usd: float = 0.0
    global_evidence: list[MoneyEvidence] = field(default_factory=list)
    mainland_evidence: list[MoneyEvidence] = field(default_factory=list)
    fetched_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
