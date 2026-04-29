from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from .extract import extract_amounts_for_target
from .fetch import discover_candidate_links, fetch_text
from .funds import group_by_manager
from .fx import FxClient, fx_as_of_date
from .models import FundRecord, ManagerResult, ManagerSource, MoneyEvidence
from .report import write_excel_report


def run_tracker(
    *,
    global_funds: list[FundRecord],
    mainland_share_classes: list[FundRecord],
    manager_sources: dict[str, ManagerSource],
    selected_managers: set[str] | None = None,
) -> dict:
    session = requests.Session()
    fx_client = FxClient(session=session)
    global_by_manager = group_by_manager(global_funds)
    mainland_by_manager = group_by_manager(mainland_share_classes)
    manager_names = sorted(set(global_by_manager) | set(mainland_by_manager))
    if selected_managers:
        manager_names = [name for name in manager_names if name in selected_managers]

    results: list[ManagerResult] = []
    for manager in manager_names:
        source = manager_sources.get(manager)
        if not source:
            results.append(
                ManagerResult(
                    manager=manager,
                    official_site="",
                    errors=[f"No manager source configured for {manager}."],
                )
            )
            continue
        if not source.enabled:
            continue
        results.append(
            scrape_manager(
                source=source,
                global_targets=global_by_manager.get(manager, []),
                mainland_targets=mainland_by_manager.get(manager, []),
                session=session,
                fx_client=fx_client,
            )
        )

    return {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "fx_as_of_date": fx_as_of_date(),
        "fx_rates_to_usd": _fx_rates_for_output(fx_client),
        "results": [manager_result_to_dict(result) for result in results],
    }


def scrape_manager(
    *,
    source: ManagerSource,
    global_targets: list[FundRecord],
    mainland_targets: list[FundRecord],
    session: requests.Session,
    fx_client: FxClient,
) -> ManagerResult:
    result = ManagerResult(manager=source.name, official_site=source.official_site)
    urls = list(dict.fromkeys(source.seed_urls))
    if source.discover_links:
        for seed_url in source.seed_urls:
            try:
                urls.extend(discover_candidate_links(session, seed_url, source.max_discovered_links))
            except Exception as exc:  # noqa: BLE001 - keep scraping other sources
                result.errors.append(f"Link discovery failed for {seed_url}: {exc}")
    urls = list(dict.fromkeys(urls))

    text_sources: list[tuple[str, str]] = []
    for url in urls:
        try:
            text, final_url = fetch_text(session, url)
            result.fetched_urls.append(final_url)
            text_sources.append((final_url, text))
        except Exception as exc:  # noqa: BLE001 - keep scraping other URLs
            result.errors.append(f"Fetch failed for {url}: {exc}")

    result.global_evidence = collect_evidence(global_targets, text_sources, fx_client)
    result.mainland_evidence = collect_evidence(mainland_targets, text_sources, fx_client)
    result.global_total_usd = sum(item.amount_usd for item in result.global_evidence)
    result.mainland_total_usd = sum(item.amount_usd for item in result.mainland_evidence)
    if not result.global_evidence:
        result.errors.append("No global fund AUM evidence extracted.")
    if not result.mainland_evidence:
        result.errors.append("No mainland share-class AUM evidence extracted.")
    return result


def collect_evidence(
    targets: list[FundRecord],
    text_sources: list[tuple[str, str]],
    fx_client: FxClient,
) -> list[MoneyEvidence]:
    evidence: list[MoneyEvidence] = []
    seen: set[tuple[str, str, str, str]] = set()
    for target in targets:
        for source_url, text in text_sources:
            required_term_groups = share_class_term_groups(target)
            aliases = english_aliases_for_target(target, required_term_groups)
            for extracted in extract_amounts_for_target(
                text,
                target.name,
                source_url,
                extra_aliases=aliases,
                required_term_groups=required_term_groups,
            ):
                key = (
                    extracted.target_name,
                    extracted.currency,
                    f"{extracted.amount:.4f}",
                    extracted.source_url,
                )
                if key in seen:
                    continue
                seen.add(key)
                rate = fx_client.rate_to_usd(extracted.currency)
                evidence.append(
                    MoneyEvidence(
                        target_name=extracted.target_name,
                        amount=extracted.amount,
                        currency=extracted.currency,
                        amount_usd=extracted.amount * rate,
                        fx_rate_to_usd=rate,
                        source_url=extracted.source_url,
                        label=extracted.label,
                        context=extracted.context,
                    )
                )
    return evidence


def english_aliases_for_target(target: FundRecord, required_term_groups: list[list[str]]) -> list[str]:
    if not target.english_name:
        return []
    if target.source_kind == "mainland_share_class" and not required_term_groups:
        return []
    return [target.english_name]


def share_class_term_groups(target: FundRecord) -> list[list[str]]:
    if target.source_kind != "mainland_share_class":
        return []
    name = target.name.upper()
    groups: list[list[str]] = []
    if "PRC" in name:
        groups.append(["PRC"])
    if "CNY" in name:
        groups.append(["CNY", "RMB", "CNH"])
    if "USD" in name:
        groups.append(["USD"])
    if "HKD" in name:
        groups.append(["HKD"])
    if "HDG" in name or "对冲" in target.name or "對沖" in target.name:
        groups.append(["HDG", "HEDGED", "对冲", "對沖"])
    if any(token in target.name for token in ("累积", "累計", "累计")):
        groups.append(["acc", "accumulation", "accumulative", "累积", "累計", "累计"])
    if any(token in target.name for token in ("派息", "分派")):
        groups.append(["dist", "distribution", "dividend", "monthly", "派息", "分派"])
    return groups


def manager_result_to_dict(result: ManagerResult) -> dict:
    return {
        "manager": result.manager,
        "official_site": result.official_site,
        "global_total_usd": round(result.global_total_usd, 2),
        "mainland_total_usd": round(result.mainland_total_usd, 2),
        "global_evidence": [asdict(item) for item in result.global_evidence],
        "mainland_evidence": [asdict(item) for item in result.mainland_evidence],
        "fetched_urls": result.fetched_urls,
        "errors": result.errors,
    }


def write_outputs(payload: dict, output_dir: Path) -> tuple[Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_date = datetime.now().date().isoformat()
    json_path = output_dir / f"northbound_aum_{run_date}.json"
    csv_path = output_dir / f"northbound_aum_{run_date}.csv"
    latest_json = output_dir / "latest.json"
    latest_csv = output_dir / "latest.csv"
    xlsx_path = output_dir / f"northbound_aum_{run_date}.xlsx"
    latest_xlsx = output_dir / "latest.xlsx"

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    json_path.write_text(content, encoding="utf-8")
    latest_json.write_text(content, encoding="utf-8")
    write_csv(payload, csv_path)
    write_csv(payload, latest_csv)
    fund_data_path = Path(payload.get("fund_data_path") or "data/northbound_mutual_funds_20260427.json")
    write_excel_report(payload, fund_data_path, xlsx_path, report_date=run_date)
    write_excel_report(payload, fund_data_path, latest_xlsx, report_date=run_date)
    return json_path, csv_path, latest_json, latest_csv, xlsx_path, latest_xlsx


def write_csv(payload: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "manager",
                "official_site",
                "global_total_usd",
                "mainland_total_usd",
                "global_evidence_count",
                "mainland_evidence_count",
                "error_count",
            ],
        )
        writer.writeheader()
        for item in payload["results"]:
            writer.writerow(
                {
                    "manager": item["manager"],
                    "official_site": item["official_site"],
                    "global_total_usd": item["global_total_usd"],
                    "mainland_total_usd": item["mainland_total_usd"],
                    "global_evidence_count": len(item["global_evidence"]),
                    "mainland_evidence_count": len(item["mainland_evidence"]),
                    "error_count": len(item["errors"]),
                }
            )


def _fx_rates_for_output(fx_client: FxClient) -> dict[str, float]:
    rates = dict(fx_client.cache)
    if "CNY" not in rates:
        try:
            rates["CNY"] = fx_client.rate_to_usd("CNY")
        except Exception:  # noqa: BLE001 - JSON/CSV outputs can still be written
            pass
    return rates
