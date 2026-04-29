from __future__ import annotations

import argparse
from pathlib import Path

from .funds import load_fund_records
from .sources import load_manager_sources
from .tracker import run_tracker, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track northbound mutual recognition fund AUM.")
    parser.add_argument("--fund-data", type=Path, default=Path("data/northbound_mutual_funds_20260427.json"))
    parser.add_argument("--sources", type=Path, default=Path("config/manager_sources.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--manager", action="append", default=[], help="Run only the specified manager. Repeatable.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    global_funds, mainland_share_classes = load_fund_records(args.fund_data)
    manager_sources = load_manager_sources(args.sources)
    selected_managers = set(args.manager) if args.manager else None
    payload = run_tracker(
        global_funds=global_funds,
        mainland_share_classes=mainland_share_classes,
        manager_sources=manager_sources,
        selected_managers=selected_managers,
    )
    json_path, csv_path, latest_json, latest_csv = write_outputs(payload, args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {latest_json}")
    print(f"Wrote {latest_csv}")


if __name__ == "__main__":
    main()

