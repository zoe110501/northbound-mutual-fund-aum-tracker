from __future__ import annotations

import json
from pathlib import Path

from .models import FundRecord


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def infer_manager(name: str, manager: str) -> str:
    if manager:
        return manager
    if "百达" in name:
        return "百达资产管理(香港)"
    return manager


def load_fund_records(path: Path) -> tuple[list[FundRecord], list[FundRecord]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sheets = payload["sheets"]
    funds = [
        FundRecord(
            fund_code=_clean_text(row.get("fund_code")),
            name=_clean_text(row.get("name")),
            management_company=infer_manager(_clean_text(row.get("name")), _clean_text(row.get("management_company"))),
            source_kind="global_fund",
        )
        for row in sheets["funds"]
        if _clean_text(row.get("name")) and infer_manager(_clean_text(row.get("name")), _clean_text(row.get("management_company")))
    ]
    mainland_share_classes = [
        FundRecord(
            fund_code=_clean_text(row.get("fund_code")),
            name=_clean_text(row.get("name")),
            management_company=infer_manager(_clean_text(row.get("name")), _clean_text(row.get("management_company"))),
            source_kind="mainland_share_class",
        )
        for row in sheets["mainland_share_classes"]
        if _clean_text(row.get("name")) and infer_manager(_clean_text(row.get("name")), _clean_text(row.get("management_company")))
    ]
    return funds, mainland_share_classes


def group_by_manager(records: list[FundRecord]) -> dict[str, list[FundRecord]]:
    grouped: dict[str, list[FundRecord]] = {}
    for record in records:
        grouped.setdefault(record.management_company, []).append(record)
    return grouped
