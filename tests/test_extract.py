from northbound_fund_aum_tracker.extract import extract_amounts_for_target, parse_amount


def test_parse_amount_units():
    assert parse_amount("12.5", "亿") == 1_250_000_000
    assert parse_amount("3.2", "million") == 3_200_000
    assert parse_amount("1,000", "") == 1_000


def test_extract_amounts_for_target_near_aum_label():
    text = """
    摩根亚洲总收益债券PRC-USD累积
    Fund size / Net Asset Value: USD 123.45 million as of month end.
    """
    amounts = extract_amounts_for_target(text, "摩根亚洲总收益债券PRC-USD累积", "https://example.com/fund")
    assert len(amounts) == 1
    assert amounts[0].currency == "USD"
    assert amounts[0].amount == 123_450_000


def test_extract_financial_report_amounts_in_thousands():
    text = """
    JPMorgan Funds - Asia Total Return Bond Fund
    Financial statements
    US$'000
    Net asset value attributable to shareholders 456,789
    摩根亚洲总收益债券PRC-USD累积
    """
    amounts = extract_amounts_for_target(text, "摩根亚洲总收益债券PRC-USD累积", "https://example.com/report.pdf")
    assert len(amounts) == 1
    assert amounts[0].currency == "USD"
    assert amounts[0].amount == 456_789_000
