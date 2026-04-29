from __future__ import annotations

import re
from dataclasses import dataclass

from .fx import normalize_currency


AMOUNT_PATTERN = re.compile(
    r"(?P<currency>US\$|HK\$|USD|HKD|CNY|RMB|CNH|EUR|GBP|SGD|AUD|CAD|JPY|[$¥￥])\s*"
    r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit>亿|億元|億元港幣|亿元|万|萬|million|mn|m|billion|bn)?"
    r"|(?P<amount2>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<unit2>亿|億元|億元港幣|亿元|万|萬|million|mn|m|billion|bn)?\s*"
    r"(?P<currency2>US\$|HK\$|USD|HKD|CNY|RMB|CNH|EUR|GBP|SGD|AUD|CAD|JPY)",
    re.IGNORECASE,
)

RELEVANT_LABEL_PATTERN = re.compile(
    r"AUM|assets? under management|fund size|fund assets|total net assets|net assets|"
    r"net asset value attributable|"
    r"资产净值|資產淨值|基金规模|基金規模|總資產|总资产|資產值|资产值",
    re.IGNORECASE,
)

PROHIBITED_AMOUNT_CONTEXT_PATTERN = re.compile(
    r"latest\s+nav|nav per unit|current nav|valuation date|isin|bloomberg|morningstar rating|quota|qfii|safe under|"
    r"award|best performer|asset manager of the year",
    re.IGNORECASE,
)

REPORT_SCALE_PATTERN = re.compile(
    r"(?P<currency>US\$|HK\$|USD|HKD|CNY|RMB|CNH|EUR|GBP|SGD|AUD|CAD|JPY)\s*['’]?\s*000|"
    r"in thousands of (?P<currency_words>US dollars|Hong Kong dollars|Renminbi|RMB|Euro|Pound Sterling|Singapore dollars)",
    re.IGNORECASE,
)

REPORT_LABEL_AMOUNT_PATTERN = re.compile(
    r"(?:net asset value attributable to shareholders|net asset value|NAV|"
    r"资产净值|資產淨值|基金规模|基金規模)[^\d]{0,120}"
    r"(?P<amount>\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedAmount:
    target_name: str
    amount: float
    currency: str
    label: str
    context: str
    source_url: str


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def target_aliases(target_name: str, extra_aliases: list[str] | None = None) -> list[str]:
    aliases = {target_name.strip()}
    for alias in extra_aliases or []:
        aliases.add(alias.strip())
    for token in ("PRC-", "PRC", "CNY HDG", "USD", "累积", "累計", "派息", "累计", "每月"):
        if token in target_name:
            aliases.add(target_name.replace(token, "").strip())
    return [item for item in aliases if len(item) >= 4]


def extract_amounts_for_target(
    text: str,
    target_name: str,
    source_url: str,
    extra_aliases: list[str] | None = None,
    required_term_groups: list[list[str]] | None = None,
) -> list[ExtractedAmount]:
    normalized = normalize_text(text)
    windows: list[str] = []
    lookahead = 5000 if source_url.lower().endswith(".pdf") else 1200
    for alias in target_aliases(target_name, extra_aliases):
        for match in re.finditer(re.escape(alias), normalized, flags=re.IGNORECASE):
            start = max(match.start() - 1200, 0)
            end = min(match.end() + lookahead, len(normalized))
            windows.append(normalized[start:end])

    if not windows:
        return []

    results: list[ExtractedAmount] = []
    seen: set[tuple[str, str, str]] = set()
    for window in windows:
        if not _has_required_terms(window, required_term_groups):
            continue
        if not RELEVANT_LABEL_PATTERN.search(window):
            continue
        label = _best_label(window)
        for match in AMOUNT_PATTERN.finditer(window):
            currency = match.group("currency") or match.group("currency2")
            raw_amount = match.group("amount") or match.group("amount2")
            unit = match.group("unit") or match.group("unit2") or ""
            if not currency or not raw_amount:
                continue
            amount = parse_amount(raw_amount, unit) * _implied_scale(window, match.start())
            if amount <= 0:
                continue
            context = _context_around(window, match.start(), match.end())
            if not _is_valid_amount_match(window, match.start(), required_term_groups):
                continue
            key = (normalize_currency(currency), f"{amount:.4f}", context[:80])
            if key in seen:
                continue
            seen.add(key)
            results.append(
                ExtractedAmount(
                    target_name=target_name,
                    amount=amount,
                    currency=normalize_currency(currency),
                    label=label,
                    context=context,
                    source_url=source_url,
                )
            )
        scaled_currency, multiplier = _report_scale(window)
        if scaled_currency:
            for match in REPORT_LABEL_AMOUNT_PATTERN.finditer(window):
                amount = parse_amount(match.group("amount"), "") * multiplier
                context = _context_around(window, match.start(), match.end())
                if not _is_valid_amount_context(context, required_term_groups):
                    continue
                key = (scaled_currency, f"{amount:.4f}", context[:80])
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    ExtractedAmount(
                        target_name=target_name,
                        amount=amount,
                        currency=scaled_currency,
                        label=_best_label(match.group(0)),
                        context=context,
                        source_url=source_url,
                    )
                )
    return results


def _has_required_terms(window: str, required_term_groups: list[list[str]] | None) -> bool:
    if not required_term_groups:
        return True
    normalized_window = window.lower()
    return all(any(term.lower() in normalized_window for term in group) for group in required_term_groups)


def _is_valid_amount_context(context: str, required_term_groups: list[list[str]] | None = None) -> bool:
    if PROHIBITED_AMOUNT_CONTEXT_PATTERN.search(context):
        return False
    if not _has_required_terms(context, required_term_groups):
        return False
    return bool(RELEVANT_LABEL_PATTERN.search(context))


def _is_valid_amount_match(
    window: str,
    amount_start: int,
    required_term_groups: list[list[str]] | None = None,
) -> bool:
    prefix = window[max(amount_start - 120, 0) : amount_start]
    relevant_matches = list(RELEVANT_LABEL_PATTERN.finditer(prefix))
    if not relevant_matches:
        return False
    prohibited_matches = list(PROHIBITED_AMOUNT_CONTEXT_PATTERN.finditer(prefix))
    if prohibited_matches and prohibited_matches[-1].end() >= relevant_matches[-1].start():
        return False
    return _has_required_terms(_context_around(window, amount_start, amount_start), required_term_groups)


def _implied_scale(window: str, amount_start: int) -> int:
    prefix = window[max(amount_start - 120, 0) : amount_start].lower()
    if re.search(r"fund size\s*\(m\)|total fund size\s*\(m\)|net assets\s*\(m\)", prefix):
        return 1_000_000
    return 1


def parse_amount(raw_amount: str, unit: str) -> float:
    value = float(raw_amount.replace(",", ""))
    unit = unit.lower()
    multipliers = {
        "亿": 100_000_000,
        "亿元": 100_000_000,
        "億元": 100_000_000,
        "億元港幣": 100_000_000,
        "万": 10_000,
        "萬": 10_000,
        "million": 1_000_000,
        "mn": 1_000_000,
        "m": 1_000_000,
        "billion": 1_000_000_000,
        "bn": 1_000_000_000,
    }
    return value * multipliers.get(unit, 1)


def _best_label(window: str) -> str:
    match = RELEVANT_LABEL_PATTERN.search(window)
    return match.group(0) if match else "amount"


def _report_scale(window: str) -> tuple[str, int]:
    match = REPORT_SCALE_PATTERN.search(window)
    if not match:
        return "", 1
    currency = match.group("currency")
    if not currency:
        currency = {
            "us dollars": "USD",
            "hong kong dollars": "HKD",
            "renminbi": "CNY",
            "rmb": "CNY",
            "euro": "EUR",
            "pound sterling": "GBP",
            "singapore dollars": "SGD",
        }.get((match.group("currency_words") or "").lower(), "")
    return normalize_currency(currency), 1_000


def _context_around(text: str, start: int, end: int) -> str:
    return text[max(start - 160, 0) : min(end + 160, len(text))]
