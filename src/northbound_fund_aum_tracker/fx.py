from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import requests


@dataclass
class FxClient:
    session: requests.Session = field(default_factory=requests.Session)
    cache: dict[str, float] = field(default_factory=dict)

    def rate_to_usd(self, currency: str) -> float:
        currency = normalize_currency(currency)
        if currency == "USD":
            return 1.0
        if currency in self.cache:
            return self.cache[currency]

        rate = self._frankfurter_rate(currency)
        self.cache[currency] = rate
        return rate

    def _frankfurter_rate(self, currency: str) -> float:
        url = "https://api.frankfurter.app/latest"
        response = self.session.get(url, params={"from": currency, "to": "USD"}, timeout=20)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        try:
            return float(payload["rates"]["USD"])
        except KeyError as exc:
            raise RuntimeError(f"Frankfurter did not return USD rate for {currency}: {payload}") from exc


def normalize_currency(value: str) -> str:
    value = value.strip().upper()
    aliases = {
        "$": "USD",
        "US$": "USD",
        "USD$": "USD",
        "HK$": "HKD",
        "HKD$": "HKD",
        "RMB": "CNY",
        "CNH": "CNY",
        "¥": "CNY",
        "￥": "CNY",
    }
    return aliases.get(value, value)


def fx_as_of_date() -> str:
    return date.today().isoformat()

