from pathlib import Path

from northbound_fund_aum_tracker.funds import load_fund_records


def test_load_fund_records():
    funds, mainland = load_fund_records(Path("data/northbound_mutual_funds_20260427.json"))
    assert len(funds) == 44
    assert len(mainland) == 248
    assert any(item.management_company == "摩根基金(亚洲)" for item in mainland)
    assert funds[0].english_name == "BEA Union Investment Series - BEA Union Investment Asian Bond and Currency Fund"
    assert mainland[0].english_name == "JPMorgan Asian Total Return Bond Fund"
