from pathlib import Path

from northbound_fund_aum_tracker.funds import load_fund_records
from northbound_fund_aum_tracker.sources import load_manager_sources


def test_manager_sources_cover_fund_managers():
    funds, mainland = load_fund_records(Path("data/northbound_mutual_funds_20260427.json"))
    sources = load_manager_sources(Path("config/manager_sources.json"))
    managers = {record.management_company for record in [*funds, *mainland]}
    missing = managers - set(sources)
    assert missing == set()

